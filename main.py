from parameter import Parameter
from session import Session
from condition import Condition
from spider import Spider
from error import ErrorList
from config import Config
from datetime import datetime
import logging
import sys
import json
import argparse


def main():
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

    parser = argparse.ArgumentParser(description='Court Spider')
    parser.add_argument('-s', '--spider', nargs='?', choices=['date', 'district'], const='date',
                        help='Start a spider to crawl data by date or by district')
    parser.add_argument('-d', '--downloader', action='store_true', help='Start a downloader')
    args = parser.parse_args()

    if args.spider is None:
        if args.downloader is False:
            logging.error('Please specify spider or downloader to run.')
            parser.print_help()
            exit(1)
        else:
            logging.info('Downloader running.')
    if args.spider is not None:
        if args.downloader is True:
            logging.error('Choose one from spider or downloader, not both.')
            parser.print_help()
            exit(1)
        elif args.spider == 'date':
            logging.info('Spider running to crawl data by date.')
            crawl_by_district()
        elif args.spider == 'district':
            logging.info('Spider running to crawl data by district.')


def crawl_by_district():
    # Read config
    start_dist, start_date = None, None
    start_info = Config['start']
    if 'district' in start_info and start_info['district'] is not None:
        start_dist = start_info['district']
        logging.info('Start District: {}'.format(start_dist))
    if 'date' in start_info and start_info['date'] is not None:
        start_date = start_info['date']
        logging.info('Start Date: {}'.format(start_date.strftime("%Y-%m-%d")))

    max_retry = Config['config']['maxRetry']
    data_file = open('./data/data {}.txt'.format(datetime.now().strftime('%Y-%m-%d %H-%M-%S')), 'a', encoding='utf-8')

    s = Session()
    c = Condition()
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
                print(json.dumps(list(spider.district(condition=c)), ensure_ascii=False), file=f)

            for dist in spider.district(condition=c):
                # Find the district to start
                if not start:
                    if dist == start_dist:
                        start = True
                    else:
                        continue
                logging.info(dist)
                c1 = c.district(dist)

                # If time_interval is interrupted, continue from the start_date
                cur_date = None
                if start_date is not None:
                    cur_date = start_date
                    start_date = None

                # Variables for retry
                dist_success = False
                dist_retry = max_retry
                while not dist_success:
                    try:
                        for time_interval in spider.time_interval(condition=c1, start_date=cur_date):
                            logging.info('{0} {1} {2} {3}'.format(dist,
                                                                  time_interval[0].strftime('%Y-%m-%d'),
                                                                  time_interval[1].strftime('%Y-%m-%d'),
                                                                  time_interval[2]))
                            cur_date = time_interval[0]
                            time_success = False
                            time_retry = max_retry
                            index = 1
                            while not time_success:
                                try:
                                    for item, idx in spider.content_list(
                                            param=Parameter(param=str(c1.date(time_interval[0], time_interval[1])),
                                                            sess=s),
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
                                    time_retry -= 1
                                    if time_retry <= 0:
                                        s.switch_proxy()
                                        time_retry = max_retry
                        dist_success = True
                    except None as e:
                        logging.error('Error when fetch time interval: {0}'.format(str(e)))
                        dist_retry -= 1
                        if dist_retry <= 0:
                            s.switch_proxy()
                            dist_retry = max_retry
            total_success = True
        except ErrorList as e:
            logging.error('Error when fetch dist information: {0}'.format(str(e)))
            s.switch_proxy()
    data_file.close()


if __name__ == '__main__':
    main()
