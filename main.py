from parameter import Parameter
from session import Session
from config import Config
from spider import Spider
from error import NetworkException

from datetime import datetime
# import time, random
import logging

if __name__ == '__main__':

    logging.basicConfig(format='[%(levelname)s] %(asctime)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S',
                        level=logging.INFO)
    s = Session()
    c = Config()
    spider = Spider(sess=s)
    # error_log = open('./log/error-{}.txt'.format(datetime.now().strftime('%Y-%m-%d %H-%M-%S')), 'w', encoding='utf-8')
    data_log = open('./log/data-{}.txt'.format(datetime.now().strftime('%Y-%m-%d %H-%M-%S')), 'w', encoding='utf-8')
    start = False
    for dist in spider.district(config=c):
        if not start:
            if dist == '新疆维吾尔自治区':
                start = True
            else:
                continue
        logging.info(dist)
        c1 = c.district(dist)
        # retry if encounter network error
        dist_success = False
        while not dist_success:
            try:
                for d in spider.time_interval(config=c1):
                    logging.info((dist, d[0].strftime('%Y-%m-%d'), d[1].strftime('%Y-%m-%d')))
                    time_success = False
                    while not time_success:
                        try:
                            for item in spider.content_list(param=Parameter(param=str(c1.date(d[0], d[1])), sess=s), page=20,
                                                            order='法院层级', direction='asc'):
                                print(item, file=data_log)
                                # print(item['id'], item['name'])
                                # try:
                                #     spider.download_doc(item['id'])
                                # except:
                                #     print(item['id'], file=error_log)
                            time_success = True
                        except NetworkException as e:
                            logging.error('Error when fetch content list: {0}'.format(e.value))
                dist_success = True
            except NetworkException as e:
                logging.error('Error when fetch time interval: {0}'.format(e.value))
    data_log.close()
    # error_log.close()
