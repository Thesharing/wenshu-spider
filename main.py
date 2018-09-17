from parameter import Parameter
from session import Session
from config import Config
from spider import Spider
from datetime import datetime
import time, random

if __name__ == '__main__':

    s = Session()
    c = Config()
    # parameter = Parameter(param=str(c), sess=s)
    spider = Spider(sess=s)
    error_log = open('./log/error-{}.txt'.format(datetime.now().strftime('%Y-%m-%d %H-%M-%S')), 'w', encoding='utf-8')
    data_log = open('./log/data-{}.txt'.format(datetime.now().strftime('%Y-%m-%d %H-%M-%S')), 'w', encoding='utf-8')
    start = False
    for dist in spider.district(config=c):
        if not start:
            if dist == '新疆维吾尔自治区':
                start = True
            else:
                continue
        print(dist)
        c1 = c.district(dist)
        for d in spider.time_interval(config=c1):
            print(dist, d[0].strftime('%Y-%m-%d'), d[1].strftime('%Y-%m-%d'))
            for item in spider.content_list(param=Parameter(param=str(c1.date(d[0], d[1])), sess=s), page=20,
                                            order='法院层级', direction='asc'):
                print(item, file=data_log)
                # print(item['id'], item['name'])
                # try:
                #     spider.download_doc(item['id'])
                # except:
                #     print(item['id'], file=error_log)
            time.sleep(random.random() * 2)
    # page: 每页几条; order: 排序标准; direction: 顺序 (asc - 正序 desc - 倒序)
    # for i in spider.content_list(param=parameter, page=20, order='法院层级', direction='asc'):
    #     print(i)
    error_log.close()
    data_log.close()
