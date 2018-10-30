import logging
import re
import os
from urllib import parse

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
            'court_content': re.compile(r'\"Html\":\"(.*?)\"')
        }
        with open('./html/content.html', 'r', encoding='utf-8') as f:
            self.html = f.read()

    def _court_info(self, doc_id):
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
        return_data = req.text.replace('\\', '')
        with open('./content/{}.txt'.format(doc_id), 'w', encoding='utf-8') as f:
            f.write(return_data)
        read_count = re.findall(r'"浏览：(\d*)次"', return_data)[0]
        court_title = re.findall(r'\"Title\":\"(.*?)\"', return_data)[0]
        court_date = re.findall(r'\"PubDate\":\"(.*?)\"', return_data)[0]
        court_content = re.findall(r'\"Html\":\"(.*?)\"', return_data)[0]
        return [court_title, court_date, read_count, court_content, return_data]

    def _download_file(self, doc_id, court_title, court_date, read_count, court_content):
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

    def _persistence(self, doc_id, raw_data):
        pass

    def download_doc(self, doc_id):
        """
        根据文书DocID下载doc文档
        """
        court_title, court_date, read_count, court_content, raw_data = self._court_info(doc_id)
        self._download_file(doc_id, court_title, court_date, read_count, court_content)
