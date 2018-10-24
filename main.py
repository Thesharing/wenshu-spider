from parameter import Parameter
from session import Session
from config import Config
from spider import Spider
from error import ErrorList
from util import CustomJsonDecoder
from datetime import datetime
import os
import logging
import sys
import json


def prepare():
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

    start_dist, start_date = None, None
    if os.path.isfile('start.json'):
        with open('start.json', 'r', encoding='utf-8') as f:
            try:
                decoder = CustomJsonDecoder()
                start_info = decoder.decode(f.read().strip())
                if 'district' in start_info and start_info['district'] is not None:
                    start_dist = start_info['district']
                    logging.info('Start District: {}'.format(start_dist))
                if 'date' in start_info and start_info['date'] is not None:
                    start_date = start_info['date']
                    logging.info('Start Date: {}'.format(start_date.strftime("%Y-%m-%d")))
            except (json.decoder.JSONDecodeError, KeyError, ValueError):
                logging.error(
                    'Format of start.json is incorrect, which should be: {"district": "xx省", "date": "xxxx-xx-xx"}')

    retry_time = 10
    data_file = open('./data/data {}.txt'.format(datetime.now().strftime('%Y-%m-%d %H-%M-%S')), 'a', encoding='utf-8')

    return start_dist, start_date, retry_time, data_file


def crawl_by_district(start_dist, start_date, retry_time, data_file):
    s = Session()
    c = Config()
    spider = Spider(sess=s)

    total_success = False
    while not total_success:
        try:
            if start_dist is not None:
                start = False
            else:
                start = True

            # log the distribution of district
            with open('district_list.txt', 'w', encoding='utf-8') as f:
                print(json.dumps(list(spider.district(config=c)), ensure_ascii=False), file=f)

            for dist in spider.district(config=c):
                if not start:
                    if dist == start_dist:
                        start = True
                    else:
                        continue
                logging.info(dist)
                c1 = c.district(dist)
                dist_success = False
                first_retry_time = retry_time
                cur_date = None  # if time_interval is interrupted, continue from the start_date
                if start_date is not None:
                    cur_date = start_date
                    start_date = None
                while not dist_success:
                    try:
                        for d in spider.time_interval(config=c1, start_date=cur_date):
                            logging.info(
                                '{0} {1} {2} {3}'.format(dist, d[0].strftime('%Y-%m-%d'), d[1].strftime('%Y-%m-%d'),
                                                         d[2]))
                            cur_date = d[0]
                            time_success = False
                            second_retry_time = retry_time
                            index = 1
                            while not time_success:
                                try:
                                    for item, idx in spider.content_list(
                                            param=Parameter(param=str(c1.date(d[0], d[1])), sess=s),
                                            page=20, order='法院层级', direction='asc', index=index):
                                        print(item, file=data_file)
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
                                        second_retry_time = retry_time
                        dist_success = True
                    except ErrorList as e:
                        logging.error('Error when fetch time interval: {0}'.format(str(e)))
                        first_retry_time -= 1
                        if first_retry_time <= 0:
                            s.switch_proxy()
                            first_retry_time = retry_time
            total_success = True
        except ErrorList as e:
            logging.error('Error when fetch dist information: {0}'.format(str(e)))
            s.switch_proxy()
    data_file.close()


if __name__ == '__main__':
    crawl_by_district(*prepare())
