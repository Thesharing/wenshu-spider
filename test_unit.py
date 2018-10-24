from parameter import Parameter
from session import Session
from condition import Condition
from spider import Spider
from datetime import datetime
import execjs
import logging
from util import CustomJsonEncoder, CustomJsonDecoder


def test_vl5x(vjkl5):
    with open('./js/vl5x.js') as f:
        js = f.read()
        js_vl5x = execjs.compile(js)
        print(js_vl5x.call('GetVl5x', vjkl5))


def test_spider():
    s = Session()
    c = Condition()
    # parameter = Parameter(param=str(c), sess=s)
    spider = Spider(sess=s)
    # page: 每页几条; order: 排序标准; direction: 顺序 (asc - 正序 desc - 倒序)
    print(spider.tree_content(
        param=Parameter(param=str(c.district('西藏自治区').date(datetime(1991, 1, 1), datetime(2018, 9, 15))),
                        sess=s)))
    for i in spider.content_list(param=Parameter(param=
                                                 str(c.district('西藏自治区').date(datetime(1991, 1, 1),
                                                                              datetime(2018, 9, 15)))),
                                 page=20, order='法院层级', direction='asc'):
        print(i)


def test_logging():
    logging.info('Test')


def test_util():
    e = CustomJsonEncoder()
    d = CustomJsonDecoder()
    t = {
        'district': '山西省',
        'date': '2018-10-01'
    }
    s = e.encode(t)
    print(s)
    t = d.decode(s)
    print(t)


def test_config():
    from config import Config
    print(Config)


if __name__ == '__main__':
    test_config()
