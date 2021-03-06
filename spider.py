import json
import execjs
import re
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

        self.logger = logging.getLogger('spider')

        self.sess = sess

        with open('./js/docid.js') as f:
            js = f.read()
            self.js_docid = execjs.compile(js)

    def content_list(self, param: Parameter, page, order, direction, index=1, total=0) -> (dict, int):
        """
        获取内容列表
        page: 每页几条
        order: 排序标准
        direction: 顺序 (asc - 正序 desc - 倒序)
        """

        count = 0

        json_error_retry_time = 5

        while True:

            self.logger.info('第 {0} 页'.format(index))

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
                    self.logger.error('JSON Error: {}.'.format(str(e)))
                    # If there are 5 JSON errors, skip this page
                    json_error_retry_time -= 1
                    if json_error_retry_time == 0:
                        self.logger.critical('Skip the page {} for so many json errors.'.format(index))
                        index += 1
                        if index > MAX_PAGE or (total != 0 and count >= total):
                            break
                    continue
                if not len(json_data):
                    self.logger.info('Finished.')
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
                # self.logger.warning('出现验证码', end='\r')
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

    def court_tree_content(self, condition: Condition, parval: str):
        """
        获取每个省市的法院列表
        :return: A list of court names
        """
        url = 'http://wenshu.court.gov.cn/List/CourtTreeContent'
        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Host": "wenshu.court.gov.cn",
            "Origin": "http://wenshu.court.gov.cn",
            "Proxy-Connection": "keep-alive",
            "Referer": "http://wenshu.court.gov.cn/list/list/?sorttype=1&&conditions=searchWord+2+AJLX++{0}".format(
                parse.quote(str(condition))),
            "User-Agent": self.sess.user_agent,
            "X-Requested-With": "XMLHttpRequest"
        }
        data = {
            "Param": str(condition),
            "parval": parval
        }
        while True:
            r = self.sess.post(url=url, headers=headers, data=data)
            t = r.text.replace('\\', '').replace('"[', '[').replace(']"', ']')
            if len(t) <= 0:
                raise NullContentError('Receive null content in court_tree_content.')
            elif t == '"remind"' or t == '"remind key"':
                raise CheckCodeError('CheckCode Appeared in court_tree_content.')
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
        if '法院层级' in tree_dict:
            self.logger.critical('Error in court tree content for condition: {}'.format(str(condition)))
            return {'中级法院': {'ParamList': []}, '基层法院': {'ParamList': []}}
        return tree_dict

    def reason_tree_content(self, condition: Condition, parval: str):
        """
        获取父案由下所有的子案由
        :return: A list of reasons and corresponding level
        """
        url = 'http://wenshu.court.gov.cn/List/ReasonTreeContent'
        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Host": "wenshu.court.gov.cn",
            "Origin": "http://wenshu.court.gov.cn",
            "Proxy-Connection": "keep-alive",
            "Referer": "http://wenshu.court.gov.cn/list/list/?sorttype=1&&conditions=searchWord+2+AJLX++{0}".format(
                parse.quote(str(condition))),
            "User-Agent": self.sess.user_agent,
            "X-Requested-With": "XMLHttpRequest"
        }
        data = {
            "Param": str(condition),
            "parval": parval
        }
        while True:
            r = self.sess.post(url=url, headers=headers, data=data)
            t = r.text.replace('\\', '').replace('"[', '[').replace(']"', ']')
            if len(t) <= 0:
                raise NullContentError('Receive null content in reason_tree_content.')
            elif t == '"remind"' or t == '"remind key"':
                raise CheckCodeError('CheckCode Appeared in reason_tree_content.')
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
        if '法院层级' in tree_dict:
            self.logger.critical('Error in reason tree content for condition: {}'.format(str(condition)))
            return {'中级法院': {'ParamList': []}, '基层法院': {'ParamList': []}}
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
                e = start + timedelta(days=(i + 1) * period_length[period] - 1)
                if start_date is None or e >= start_date:
                    info = self.tree_content(Parameter(param=str(condition.date(s, e)), sess=self.sess))['裁判年份']
                    if info['IntValue'] < MAX_PAGE * 20 or period == quark:
                        yield s, e, info['IntValue']
                    else:
                        self.logger.debug(
                            '{} {} {}'.format(s.strftime('%Y-%m-%d'), period + 1,
                                              info['IntValue']))
                        yield from split(s, period + 1)

        def tail_5_days(s, e):
            info = self.tree_content(Parameter(param=str(condition.date(s, e)), sess=self.sess))['裁判年份']
            if info['IntValue'] < MAX_PAGE * 20:
                self.logger.debug(
                    '{} {} {}'.format(s.strftime('%Y-%m-%d'), e.strftime('%Y-%m-%d'),
                                      info['IntValue']))
                yield s, e, info['IntValue']
            else:
                cur = s
                while cur <= e:
                    if start_date is None or cur >= start_date:
                        info = self.tree_content(Parameter(param=str(condition.date(s, e)), sess=self.sess))['裁判年份']
                        yield cur, cur, info['IntValue']
                    cur = cur + timedelta(days=1)

        info = self.tree_content(Parameter(param=str(condition), sess=self.sess))['裁判年份']
        if info['IntValue'] < MAX_PAGE * 20:
            yield datetime(1990, 1, 1), datetime.today(), info['IntValue']
        else:
            for year in sorted(info['ParamList'], key=lambda item: int(item['Key']), reverse=False):
                s = datetime(int(year['Key']), 1, 1)
                e = datetime(int(year['Key']) + 1, 1, 1) - timedelta(days=1)
                if start_date is None or e > start_date:
                    if year['IntValue'] > MAX_PAGE * 20:
                        self.logger.debug('{} {} {}'.format(s.strftime('%Y-%m-%d'), 0, info['IntValue']))
                        yield from split(s, 0)
                        yield from tail_5_days(s + timedelta(days=360), e)
                    else:
                        yield s, e, year['IntValue']

    def district(self, condition: Condition, start_dist: str = None):
        info = self.tree_content(Parameter(param=str(condition), sess=self.sess))['法院地域']
        if start_dist is None:
            start = True
        else:
            start = False
        for d in sorted(info['ParamList'], key=lambda item: item['IntValue'], reverse=False):
            dist = d['Key']
            if not start:
                if dist == start_dist:
                    start = True
                    yield dist
            else:
                yield dist

    def court(self, condition: Condition, district: str, start_court: str = None):
        """
        :param condition:
        :param district:
        :param start_court: start_court will only be available for level 2
        :return: Court name, court level, court indicator, count
        """
        level_count = {'高级法院': 0, '中级法院': 0, '基层法院': 0}
        condition = condition.district(district)
        info = self.tree_content(Parameter(param=str(condition), sess=self.sess))['法院层级']
        satisfy = True
        for item in info['ParamList']:
            if item['IntValue'] > 200:
                satisfy = False
            if item['Key'] in level_count:
                level_count[item['Key']] = item['IntValue']

        if satisfy:
            for idx, (k, v) in enumerate(level_count.items()):
                if v > 0:
                    yield None, idx + 1, True, v

        else:
            start = start_court is None

            if start and level_count['高级法院'] > 0:
                yield None, 1, True, level_count['高级法院']
            middle = self.court_tree_content(condition, parval=district)['中级法院']
            for d in sorted(middle['ParamList'], key=lambda item: item['IntValue'], reverse=False):
                mid_court = d['Key']
                if not start:
                    if mid_court == start_court:
                        start = True
                if start:
                    if 0 < d['IntValue'] < 200:
                        yield mid_court, 2, False, d['IntValue']
                    else:
                        base = self.court_tree_content(condition.court(mid_court, 2, False), parval=mid_court)['基层法院']
                        if d['IntValue'] - base['IntValue'] > 0:
                            yield mid_court, 2, True, d['IntValue'] - base['IntValue']
                        for g in sorted(base['ParamList'], key=lambda item: item['IntValue'], reverse=False):
                            base_court = g['Key']
                            if g['IntValue'] > 0:
                                yield base_court, 3, False, g['IntValue']
