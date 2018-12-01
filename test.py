def test_vl5x(vjkl5):
    import execjs
    with open('./js/vl5x.js') as f:
        js = f.read()
        js_vl5x = execjs.compile(js)
        print(js_vl5x.call('GetVl5x', vjkl5))


def test_spider():
    from session import Session
    from condition import Condition
    from spider import Spider
    from parameter import Parameter
    from datetime import datetime

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
                                                                              datetime(2018, 9, 15))), sess=s),
                                 page=20, order='法院层级', direction='asc'):
        print(i)


def test_logging():
    import logging
    logging.info('Test')


def test_util():
    from util import CustomJsonEncoder, CustomJsonDecoder
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
    import config
    print(config.Config.config.maxRetry)


def test_condition():
    from condition import Condition
    print(Condition().params)


def test_court():
    from session import Session
    from condition import Condition
    from spider import Spider
    from parameter import Parameter
    from datetime import datetime
    s = Session()
    c = Condition().district('北京市')
    spider = Spider(sess=s)
    # print(spider.tree_content(param=Parameter(param=str(c), sess=s)))
    # print(spider.court_tree_content(condition=c, parval='北京市'))
    for i in spider.court(condition=c.date(start_date=datetime(2017, 5, 15), end_date=datetime(2017, 5, 16)),
                          district='广东省'):
        print(c.court(*i[0:3]), i[3])


def test_court_content_list():
    from session import Session
    from condition import Condition
    from datetime import datetime
    from spider import Spider
    s = Session()
    c = Condition().district('山东省').date(start_date=datetime(2015, 8, 28), end_date=datetime(2015, 8, 28))
    spider = Spider(sess=s)
    print(c)
    print(spider.court_tree_content(condition=c, parval='山东省'))


def tset_mongodb():
    from persistence import MongoDB
    db = MongoDB('测试')
    print(db.count({'a': 1}))
    # res = db.insert({'a': 1})
    # print(res.inserted_id)


def test_func():
    import os, time, datetime
    print(os.getpid(), datetime.datetime.now())
    time.sleep(3)


def test_multiprocessing():
    from multiprocessing import Pool
    pool = Pool(processes=8)

    for i in range(8):
        pool.apply_async(test_func)

    pool.close()
    pool.join()
    print('Done')


def test_download():
    from session import Session
    import config
    from persistence import MongoDB
    from downloader import Downloader
    s = Session()
    db = MongoDB(config.Config.search.reason.value)
    d = Downloader(sess=s, db=db)
    d.download_doc('6ae92d76-c63b-4298-bb31-a89d01085071')


def test_notifier():
    from notifier import WeChatNotifier, EmailNotifier, Notifier
    from persistence import RedisSet, MongoDB, LocalFile
    n = Notifier(
        [RedisSet('spider'), RedisSet('finish'), RedisSet('progress'), RedisSet('failed'), MongoDB('文书'),
         LocalFile('./download')],
        ongoing='spider', saved='文书', period=1)
    # n = EmailNotifier([RedisSet('spider'), RedisSet('finish'), RedisSet('progress'), RedisSet('failed'), MongoDB('文书'),
    #                    LocalFile('./download')],
    #                   ongoing='spider', saved='文书', period=1, sender='thesharing@163.com', password='HZL04291316wy',
    #                   server_addr="smtp.163.com")
    print(n.watch())


if __name__ == '__main__':
    test_notifier()
