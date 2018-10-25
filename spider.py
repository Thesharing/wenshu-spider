import json
import execjs
import re
import os
from urllib import parse
from datetime import datetime, timedelta
import logging

from parameter import Parameter
from session import Session
from condition import Condition
from error import CheckCodeError, NullContentError

MAX_PAGE = 10


class Spider:

    def __init__(self, sess: Session):

        self.sess = sess

        with open('./js/docid.js') as f:
            js = f.read()
            self.js_docid = execjs.compile(js)

    def content_list(self, param: Parameter, page, order, direction, index=1) -> (dict, int):
        """
        获取内容列表
        page: 每页几条
        order: 排序标准
        direction: 顺序 (asc - 正序 desc - 倒序)
        """

        total = 0
        count = 0

        json_error_retry_time = 5

        while True:

            logging.info('第 {0} 页'.format(index))

            # 获取数据
            url = "http://wenshu.court.gov.cn/List/ListContent"
            headers = {
                "Accept": "*/*",
                "Accept-Encoding": "gzip, deflate",
                "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "Host": "wenshu.court.gov.cn",
                "Origin": "http://wenshu.court.gov.cn",
                "Connection": "keep-alive",
                "DNT": "1",
                "Referer": "http://wenshu.court.gov.cn/list/list/?sorttype=1&number={0}&guid={1}&conditions=searchWord+QWJS+++{2}".format(
                    param.number, param.guid, parse.quote(param.param)),
                "User-Agent": self.sess.user_agent,
                "X-Requested-With": "XMLHttpRequest"
            }
            data = {
                "Param": param.param,
                "Index": index,
                "Page": page,
                "Order": order,
                "Direction": direction,
                "vl5x": param.vl5x,
                "number": param.number[0:4],
                "guid": param.guid
            }

            req = self.sess.post(url=url, headers=headers, data=data)
            req.encoding = 'utf-8'
            return_data = req.text.replace('\\', '').replace('"[', '[').replace(']"', ']') \
                .replace('＆ｌｄｑｕｏ;', '“').replace('＆ｒｄｑｕｏ;', '”')

            if return_data == '"remind"' or return_data == '"remind key"':
                raise CheckCodeError('CheckCode Appeared in content_list')
                # CheckCode(sess=self.sess)

            else:
                try:
                    json_data = json.loads(return_data)
                    json_error_retry_time = 5
                except Exception as e:
                    logging.error('JSON Error: {}.'.format(str(e)))
                    # If there are 5 JSON errors, skip this page
                    json_error_retry_time -= 1
                    if json_error_retry_time == 0:
                        logging.critical('Skip the page {} for so many json errors.'.format(index))
                        index += 1
                        if index > MAX_PAGE or (total != 0 and count >= total):
                            break
                    continue
                if not len(json_data):
                    logging.info('完成')
                    break
                else:
                    run_eval = json_data[0]['RunEval']
                    total = int(json_data[0]['Count'])
                    count = count + len(json_data) - 1
                    for i in range(1, len(json_data)):
                        case_name = json_data[i]['案件名称'] if '案件名称' in json_data[i] else ''
                        court_name = json_data[i]['法院名称'] if '法院名称' in json_data[i] else ''
                        case_number = json_data[i]['案号'] if '案号' in json_data[i] else ''
                        case_type = json_data[i]['案件类型'] if '案件类型' in json_data[i] else ''
                        trial_proc = json_data[i]['审判程序'] if '审判程序' in json_data[i] else ''
                        doc_id = json_data[i]['文书ID'] if '文书ID' in json_data[i] else ''
                        doc_id = self._decrypt_id(run_eval, doc_id)
                        date = json_data[i]['裁判日期'] if '裁判日期' in json_data[i] else ''
                        full_text = json_data[i]['裁判要旨段原文'] if '裁判要旨段原文' in json_data[i] else ''

                        data_dict = dict(
                            id=doc_id,
                            number=case_number,
                            name=case_name,
                            type=case_type,
                            date=date,
                            court=court_name,
                            proc=trial_proc,
                            text=full_text
                        )
                        yield data_dict, index

                index += 1

            param.refresh()

            if index > MAX_PAGE or (total != 0 and count >= total):
                break

    def _decrypt_id(self, run_eval, doc_id):
        """
        解密DocID
        """
        if len(doc_id) > 0:
            js = self.js_docid.call("GetJs", run_eval)
            js_objs = js.split(";;")
            js1 = js_objs[0] + ';'
            js2 = re.findall(r"_\[_\]\[_\]\((.*?)\)\(\);", js_objs[1])[0]
            key = self.js_docid.call("EvalKey", js1, js2)
            key = re.findall(r"\"([0-9a-z]{32})\"", key)[0]
            return self.js_docid.call("DecryptDocID", key, doc_id)
        else:
            return doc_id

    def _court_info(self, doc_id):
        """
        根据文书DocID获取相关信息：标题、时间、浏览次数、内容等详细信息
        """
        url = 'http://wenshu.court.gov.cn/CreateContentJS/CreateContentJS.aspx?DocID={0}'.format(doc_id)
        headers = {
            'Host': 'wenshu.court.gov.cn',
            'Origin': 'http://wenshu.court.gov.cn',
            'User-Agent': self.sess.user_agent,
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
        return [court_title, court_date, read_count, court_content]

    def download_doc(self, doc_id):
        """
        根据文书DocID下载doc文档
        """
        court_info = self._court_info(doc_id)
        url = 'http://wenshu.court.gov.cn/Content/GetHtml2Word'
        headers = {
            'Host': 'wenshu.court.gov.cn',
            'Origin': 'http://wenshu.court.gov.cn',
            'User-Agent': self.sess.user_agent
        }
        with open('./html/content.html', 'r', encoding='utf-8') as f:
            html = f.read()
        html = html.replace('court_title', court_info[0]).replace('court_date', court_info[1]). \
            replace('read_count', court_info[2]).replace('court_content', court_info[3])
        name = court_info[0]
        data = {
            'htmlStr': parse.quote(html),
            'htmlName': parse.quote(name),
            'DocID': doc_id
        }
        r = self.sess.post(url=url, headers=headers, data=data)
        filename = './download/{}.doc'.format(doc_id)
        if os.path.exists(filename):
            logging.warning('{} 重复'.format(name))
        else:
            with open(filename, 'wb') as f:
                f.write(r.content)
            logging.info('{} 已下载'.format(name))

    def tree_content(self, param: Parameter):
        """
        获取左侧类目分类
        """
        url = 'http://wenshu.court.gov.cn/List/TreeContent'
        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Host": "wenshu.court.gov.cn",
            "Origin": "http://wenshu.court.gov.cn",
            "Proxy-Connection": "keep-alive",
            "Referer": "http://wenshu.court.gov.cn/list/list/?sorttype=1&number={0}&guid={1}&conditions=searchWord+QWJS+++{2}".format(
                param.number, param.guid, parse.quote(param.param)),
            "User-Agent": self.sess.user_agent,
            "X-Requested-With": "XMLHttpRequest"
        }
        data = {
            "Param": param.param,
            "vl5x": param.vl5x,
            "number": param.number,
            "guid": param.guid
        }
        while True:
            r = self.sess.post(url=url, headers=headers, data=data)
            t = r.text.replace('\\', '').replace('"[', '[').replace(']"', ']')
            if len(t) <= 0:
                raise NullContentError('Receive null content in tree_content.')
            elif t == '"remind"' or t == '"remind key"':
                # logging.warning('出现验证码', end='\r')
                raise CheckCodeError('CheckCode Appeared in tree_content.')
                # CheckCode(sess=self.sess)
            else:
                break
        json_data = json.loads(t)
        tree_dict = {}
        for type_data in json_data:
            type_name = type_data['Key']
            type_dict = {
                'IntValue': type_data['IntValue'],
                'ParamList': []
            }
            for data in type_data['Child']:
                if data['IntValue']:
                    type_dict['ParamList'].append({'Key': data['Key'], 'IntValue': data['IntValue']})
            tree_dict[type_name] = type_dict
        return tree_dict

    def time_interval(self, condition: Condition, start_date: datetime = None):
        """
        生成时间参数
        """
        period_length = [90, 30, 10, 5, 1]
        quark = len(period_length) - 1
        period_loop = [4, 3, 3, 2, 5]

        def split(start: datetime, period: int):
            # 0 - 90天; 1 - 30天; 2 - 10天; 3 - 1天
            for i in range(0, period_loop[period]):
                s = start + timedelta(days=i * period_length[period])
                e = start + timedelta(days=(i + 1) * period_length[period])
                if start_date is None or e > start_date:
                    info = self.tree_content(Parameter(param=str(condition.date(s, e)), sess=self.sess))['裁判年份']
                    if info['IntValue'] < MAX_PAGE * 20 or period == quark:
                        yield s, e, info['IntValue']
                    else:
                        yield from split(s, period + 1)

        def tail_5_days(s, e):
            info = self.tree_content(Parameter(param=str(condition.date(s, e)), sess=self.sess))['裁判年份']
            if info['IntValue'] < MAX_PAGE * 20:
                yield s, e, info['IntValue']
            else:
                cur = s
                while cur < e:
                    yield from split(cur, quark)
                    cur = cur + timedelta(days=1)

        info = self.tree_content(Parameter(param=str(condition), sess=self.sess))['裁判年份']
        if info['IntValue'] < MAX_PAGE * 20:
            yield datetime(1990, 1, 1), datetime.today() + timedelta(days=1), info['IntValue']
        else:
            for year in sorted(info['ParamList'], key=lambda item: int(item['Key']), reverse=False):
                s = datetime(int(year['Key']), 1, 1)
                e = datetime(int(year['Key']) + 1, 1, 1)
                if start_date is None or e > start_date:
                    if year['IntValue'] > MAX_PAGE * 20:
                        yield from split(s, 0)
                        yield from tail_5_days(s + timedelta(days=360), e)
                    else:
                        yield s, e, year['IntValue']

    def district(self, condition: Condition):
        info = self.tree_content(Parameter(param=str(condition), sess=self.sess))['法院地域']
        for dist in list(
                item['Key'] for item in sorted(info['ParamList'], key=lambda item: item['IntValue'], reverse=False)):
            yield dist
