from parameter import Parameter
from session import Session
from config import Config
from spider import Spider
from error import ErrorList
from datetime import datetime
import os
import logging
import sys
import json

if __name__ == '__main__':

    if sys.version_info.major < 3 or sys.version_info.minor < 5:
        print('Python >= 3.5 is required, you are using {}.{}.'.format(sys.version_info.major, sys.version_info.minor))
        exit(1)

    logging.basicConfig(format='[%(levelname)s] %(asctime)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S',
                        level=logging.INFO,
                        handlers=[
                            logging.FileHandler(
                                './log/log {}.txt'.format(datetime.now().strftime('%Y-%m-%d %H-%M-%S')),
                                encoding='utf-8', mode='a'),
                            logging.StreamHandler()])

    if os.path.isfile('dist.txt'):
        with open('dist.txt', 'r', encoding='utf-8') as f:
            start_dist = f.read().strip()
            logging.info('Start from {}'.format(start_dist))
    else:
        start_dist = None

    RETRY_TIME = 10

    s = Session()
    c = Config()
    spider = Spider(sess=s)
    data_log = open('./data/data {}.txt'.format(datetime.now().strftime('%Y-%m-%d %H-%M-%S')), 'a', encoding='utf-8')
    total_success = False
    while not total_success:
        try:
            if start_dist is not None:
                start = False
            else:
                start = True

            # log the distribution of district
            with open('district.txt', 'w', encoding='utf-8') as f:
                print(json.dumps(spider.district(config=c)), file=f)

            for dist in spider.district(config=c):
                if not start:
                    if dist == start_dist:
                        start = True
                    else:
                        continue
                logging.info(dist)
                c1 = c.district(dist)
                dist_success = False
                first_retry_time = RETRY_TIME
                start_date = None  # if time_interval is interrupted, continue from the start_date
                while not dist_success:
                    try:
                        for d in spider.time_interval(config=c1, start_date=start_date):
                            start_date = d[0]
                            logging.info(
                                '{0} {1} {2}'.format(dist, d[0].strftime('%Y-%m-%d'), d[1].strftime('%Y-%m-%d')))
                            time_success = False
                            second_retry_time = RETRY_TIME
                            index = 1
                            while not time_success:
                                try:
                                    for item, idx in spider.content_list(
                                            param=Parameter(param=str(c1.date(d[0], d[1])), sess=s),
                                            page=20, order='法院层级', direction='asc', index=index):
                                        print(item, file=data_log)
                                        index = idx
                                        # print(item['id'], item['name'])
                                        # try:
                                        #     spider.download_doc(item['id'])
                                        # except:
                                        #     print(item['id'], file=error_log)
                                    time_success = True
                                except ErrorList as e:
                                    logging.error('Error when fetch content list: {0}'.format(str(e)))
                                    second_retry_time -= 1
                                    if second_retry_time <= 0:
                                        s.switch_proxy()
                                        second_retry_time = RETRY_TIME
                        dist_success = True
                    except ErrorList as e:
                        logging.error('Error when fetch time interval: {0}'.format(str(e)))
                        first_retry_time -= 1
                        if first_retry_time <= 0:
                            s.switch_proxy()
                            first_retry_time = RETRY_TIME
            total_success = True
        except ErrorList as e:
            logging.error('Error when fetch dist information: {0}'.format(str(e)))
            s.switch_proxy()
    data_log.close()
