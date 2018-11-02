import logging
import re
import os
from urllib import parse
from bs4 import BeautifulSoup as Soup
import json

from session import Session
from persistence import MongoDB


class Downloader:

    def __init__(self, sess: Session):
        self.logger = logging.getLogger('downloader')
        self.sess = sess
        self.pattern = {
            'read_count': re.compile(r'"浏览：(\d*)次"'),
            'court_title': re.compile(r'\"Title\":\"(.*?)\"'),
            'court_date': re.compile(r'\"PubDate\":\"(.*?)\"'),
            'court_content': re.compile(r'\"Html\":\"(.*?)\"'),
            'case_info': re.compile(r'JSON.stringfy\((.*?)\)')
        }
        with open('./html/content.html', 'r', encoding='utf-8') as f:
            self.html = f.read()

    def _get_court_info(self, doc_id):
        """
        根据文书DocID获取相关信息：标题、时间、浏览次数、内容等详细信息
        """
        url = 'http://wenshu.court.gov.cn/CreateContentJS/CreateContentJS.aspx?DocID={0}'.format(doc_id)
        headers = {
            'Host': 'wenshu.court.gov.cn',
            'Origin': 'http://wenshu.court.gov.cn',
            'User-Agent': self.sess.user_agent,
            'Referer': 'Referer: http://wenshu.court.gov.cn/content/content?DocID={}&KeyWord='.format(doc_id)
        }
        req = self.sess.get(url=url, headers=headers)
        req.encoding = 'utf-8'
        return_data = re.sub(u'\u3000', ' ', req.text.replace('\\', ''))
        with open('./content/{}.txt'.format(doc_id), 'w', encoding='utf-8') as f:
            f.write(return_data)

        read_count = self.pattern['read_count'].findall(return_data)[0]
        court_title = self.pattern['court_title'].findall(return_data)[0]
        court_date = self.pattern['court_date'].findall(return_data)[0]
        court_content = self.pattern['court_content'].findall(return_data)[0]
        case_info = self.pattern['case_info'].findall(return_data)[0]

        return [court_title, court_date, read_count, court_content, case_info, return_data]

    def _download_doc_file(self, doc_id, court_title, court_date, read_count, court_content):
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
            self.logger.warning('{} duplicated.'.format(name))
        else:
            with open(filename, 'wb') as f:
                f.write(r.content)
            self.logger.info('{} downloaded.'.format(name))

    def _extract(self, court_content, case_info):

        pass

    def _persist(self, doc_id, raw_data):
        pass

    def download_doc(self, doc_id):
        """
        根据文书DocID下载doc文档
        """
        court_title, court_date, read_count, court_content, case_info, raw_data = self._get_court_info(doc_id)
        self._download_doc_file(doc_id, court_title, court_date, read_count, court_content)


if __name__ == '__main__':
    with open('./test', 'r', encoding='utf-8') as f:
        data = f.read()
    pattern = {
        'read_count': re.compile(r'"浏览：(\d*)次"'),
        'court_title': re.compile(r'\"Title\":\"(.*?)\"'),
        'court_date': re.compile(r'\"PubDate\":\"(.*?)\"'),
        'court_content': re.compile(r'\"Html\":\"(.*?)\"'),
        'case_info': re.compile(r'JSON.stringify\((.*?)\)')
    }

    court_content = pattern['court_content'].findall(data)[0]
    soup = Soup(court_content, 'lxml')
    start_element = soup.a
    present_tag = start_element['name']
    content = {
        present_tag: []
    }
    for element in start_element.next_siblings:
        if element.name == 'a':
            present_tag = element['name']
            if present_tag not in content:
                content[present_tag] = list()
        elif element.name == 'div':
            content[present_tag].append(element.string)

    # KeyError

    case_info = json.loads(pattern['case_info'].findall(data)[0])
    info = {
        '文书ID': case_info['文书ID'],
        '案件名称': case_info['案件名称'],
        '案号': case_info['案号'],
        '案件类型': case_info['案件类型'],
        '案由': case_info['案由'],
        '法院': {
            '法院ID': case_info['法院ID'],
            '法院名称': case_info['法院名称'],
            '法院区域': case_info['法院区域'],
            '法院省份': case_info['法院省份'],
            '法院地市': case_info['法院地市'],
            '法院区县': case_info['法院区县']
        },
        '审判程序': case_info['审判程序'],
        '文书类型': case_info['文书类型'],
        '裁判日期': case_info['裁判日期'],
    }

    from pprint import pprint

    pprint(content)
