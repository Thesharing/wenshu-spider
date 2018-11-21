import logging
import re
import os
from urllib import parse
from bs4 import BeautifulSoup as Soup
from bs4.element import NavigableString
import json
import execjs

from session import Session
from persistence import MongoDB
from error import CheckCodeError


class Downloader:

    def __init__(self, sess: Session, db: MongoDB):
        self.logger = logging.getLogger('downloader')
        self.sess = sess
        self.db = db
        self.pattern = {
            'read_count': re.compile(r'"浏览：(\d*)次"'),
            'court_title': re.compile(r'\"Title\":\"(.*?)\"'),
            'court_date': re.compile(r'\"PubDate\":\"(.*?)\"'),
            'court_content': re.compile(r'\"Html\":\"(.*?)\"'),
            'case_info': re.compile(r'JSON.stringify\((.*?)\);'),
            'extra_data': re.compile(r'\(function\(\){var dirData = (.*?);if')
        }
        with open('./html/content.html', 'r', encoding='utf-8') as f:
            self.html = f.read()

    def _get_court_info(self, doc_id):
        """
        根据文书DocID获取相关信息：标题、时间、浏览次数、内容等详细信息
        """
        url = 'http://wenshu.court.gov.cn/CreateContentJS/CreateContentJS.aspx?DocID={0}'.format(doc_id)
        headers = {
            'Accept': 'text/javascript, application/javascript, */*',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'Host': 'wenshu.court.gov.cn',
            'Origin': 'http://wenshu.court.gov.cn',
            'User-Agent': self.sess.user_agent,
            'Referer': 'http://wenshu.court.gov.cn/content/content?DocID={}&KeyWord='.format(doc_id)
        }
        req = self.sess.get(url=url, headers=headers)
        req.encoding = 'utf-8'
        raw_data = re.sub(u'\u3000', ' ', req.text.replace('\\', ''))

        if '访问验证' in raw_data or 'VisitRemind' in raw_data or '并刷新该页' in raw_data:
            raise CheckCodeError('CheckCode Appeared in _get_court_info')

        with open('./content/{}.txt'.format(doc_id), 'w', encoding='utf-8') as f:
            f.write(raw_data)

        return raw_data

    def _download_doc_file(self, doc_id, raw_data):
        read_count = self.pattern['read_count'].findall(raw_data)[0]
        court_title = self.pattern['court_title'].findall(raw_data)[0]
        court_date = self.pattern['court_date'].findall(raw_data)[0]
        court_content = self.pattern['court_content'].findall(raw_data)[0]

        url = 'http://wenshu.court.gov.cn/Content/GetHtml2Word'
        headers = {
            'Host': 'wenshu.court.gov.cn',
            'Origin': 'http://wenshu.court.gov.cn',
            'User-Agent': self.sess.user_agent
        }
        html = self.html.replace('court_title', court_title).replace('court_date', court_date). \
            replace('read_count', read_count).replace('court_content', court_content)
        name = court_title
        data = {
            'htmlStr': parse.quote(html),
            'htmlName': parse.quote(name),
            'DocID': doc_id
        }
        r = self.sess.post(url=url, headers=headers, data=data)
        filename = './download/{}.doc'.format(doc_id)
        if os.path.exists(filename):
            self.logger.warning('Document 《{0}》 duplicated.'.format(name))
        else:
            with open(filename, 'wb') as f:
                f.write(r.content)
            self.logger.info('Document 《{0}》 downloaded.'.format(name))

    def _extract(self, raw_data):
        """
        Extract data from raw content
        :param raw_data: raw content downloaded by _get_court_info
        :return:
        """
        court_content = self.pattern['court_content'].findall(raw_data)[0]
        soup = Soup(court_content, 'lxml')
        content = {
            'FULLTEXT': []
        }
        start_element = soup.a
        if start_element is None:
            start_element = soup.span
            if start_element is None:
                start_element = soup.spanstyle
                if start_element is None:
                    return None
                else:
                    s = ''
                    for element in start_element.next_elements:
                        if element.name == 'pstyle':
                            content['FULLTEXT'].append(s.strip())
                            s = ''
                        if type(element) is NavigableString:
                            s += element.string
            else:
                s = ''
                for element in start_element.next_elements:
                    if element.name == 'p':
                        content['FULLTEXT'].append(s.strip())
                        s = ''
                    if type(element) is NavigableString:
                        s += element.string
        else:
            present_tag = start_element['name']
            content[present_tag] = list()
            for element in start_element.next_siblings:
                if element.name == 'a':
                    present_tag = element['name']
                    if present_tag not in content:
                        content[present_tag] = list()
                elif element.name == 'div':
                    content['FULLTEXT'].append(element.string)
                    content[present_tag].append(element.string)

        extra_data = execjs.eval(self.pattern['extra_data'].findall(raw_data)[0].replace('"', "'"))
        relate_info = dict()
        if 'RelateInfo' in extra_data:
            for item in extra_data['RelateInfo']:
                relate_info[item['name']] = item['value']
        legal_base = list()
        if 'LegalBase' in extra_data:
            for law in extra_data['LegalBase']:
                law_item = dict(法规名称=law['法规名称'] if '法规名称' in law else None, 法规内容=list())
                if 'Items' in law:
                    for legal in law['Items']:
                        law_item['法规内容'].append(dict(法条名称=legal['法条名称'] if '法条名称' in legal else None,
                                                     法条内容=list(i.strip() for i in legal['法条内容'].split('[ly]') if
                                                               len(i.strip()) > 0) if '法条内容' in legal else None))
                legal_base.append(law_item)

        case_info = json.loads(self.pattern['case_info'].findall(raw_data)[0])

        # KeyError

        return dict(文书ID=case_info['文书ID'] if '文书ID' in case_info else None,
                    案件名称=case_info['案件名称'] if '案件名称' in case_info else None,
                    案号=case_info['案号'] if '案号' in case_info else None,
                    案件类型=relate_info['案件类型'] if '案件类型' in relate_info else None,
                    法院=dict(法院ID=case_info['法院ID'] if '法院ID' in case_info else None,
                            法院名称=case_info['法院名称'] if '法院名称' in case_info else None,
                            法院区域=case_info['法院区域'] if '法院区域' in case_info else None,
                            法院省份=case_info['法院省份'] if '法院省份' in case_info else None,
                            法院地市=case_info['法院地市'] if '法院地市' in case_info else None,
                            法院区县=case_info['法院区县'] if '法院区县' in case_info else None),
                    审判程序=case_info['审判程序'] if '审判程序' in case_info else None,
                    文书类型=case_info['文书类型'] if '文书类型' in case_info else None,
                    案由=relate_info['案由'] if '案由' in relate_info else None,
                    裁判日期=relate_info['裁判日期'] if '裁判日期' in relate_info else None,
                    当事人=relate_info['当事人'].split(',') if '当事人' in relate_info else None,
                    正文=dict(文本首部=content['WBSB'] if 'WBSB' in content else None,
                            诉讼人参与信息=content['DSRXX'] if 'DSRXX' in content else None,
                            诉讼记录=content['SSJL'] if 'SSJL' in content else None,
                            事实=content['AJJBQK'] if 'AJJBQK' in content else None,
                            理由=content['CPYZ'] if 'CPYZ' in content else None,
                            判决结果=content['PJJG'] if 'PJJG' in content else None,
                            文本尾部=content['WBWB'] if 'WBWB' in content else None,
                            全文=content['FULLTEXT'] if 'FULLTEXT' in content else None),
                    附加原文=case_info['附加原文'] if '附加原文' in case_info else None,
                    补正文书=case_info['补正文书'] if '补正文书' in case_info else None,
                    文书全文类型=case_info['文书全文类型'] if '文书全文类型' in case_info else None,
                    结案方式=case_info['结案方式'] if '结案方式' in case_info else None,
                    效力层级=case_info['效力层级'] if '效力层级' in case_info else None,
                    不公开理由=case_info['不公开理由'] if '不公开理由' in case_info else None,
                    法律依据=legal_base)

    def _persist(self, doc_id, data):
        if data is None:
            self.logger.error('Doc {} cannot parse.'.format(doc_id))
        elif self.db.count({'文书ID': doc_id}) > 0:
            self.logger.warning('Doc {} duplicate in database.'.format(doc_id))
        else:
            self.db.insert(data)

    def download_doc(self, doc_id):
        """
        根据文书DocID下载doc文档
        """
        raw_data = self._get_court_info(doc_id)
        self._download_doc_file(doc_id, raw_data)
        self._persist(doc_id, self._extract(raw_data))
