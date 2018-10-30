from parameter import Parameter
from session import Session
from condition import Condition
from spider import Spider
from downloader import Downloader
from error import ExceptionList
from config import Config
from datetime import datetime
from log import Log
from persistence import RedisSet, Database
import logging
import sys
import os
import json
import argparse


def main():
    if sys.version_info.major < 3 or sys.version_info.minor < 5:
        print('Python >= 3.5 is required, you are using {}.{}.'.format(sys.version_info.major, sys.version_info.minor))
        exit(1)

    # TODO: Specify the process and

    logging.basicConfig(format='[%(levelname)s] %(asctime)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    parser = argparse.ArgumentParser(description='Court Spider')
    parser.add_argument('-s', '--spider', nargs='?', choices=['date', 'district'], const='date',
                        help='Start a spider to crawl data by date or by district')
    parser.add_argument('-d', '--downloader', nargs='?', choices=['file', 'database'], const='database',
                        help='Start a downloader')
    args = parser.parse_args()

    if args.spider is None:
        if args.downloader is None:
            logging.error('Please specify spider or downloader to run.')
            parser.print_help()
            exit(1)
        else:
            test_res = Database.test_redis()
            if test_res is not True:
                logging.error('Cannot connect to Redis: ' + str(test_res))
                exit(1)
            logger = Log.create_logger('downloader')
            logger.info('Downloader running.')
            if args.downloader == 'file':
                read_content_list()
                download()

    if args.spider is not None:
        if args.downloader is not None:
            logging.error('Choose one from spider or downloader, not both.')
            parser.print_help()
            exit(1)
        else:
            logger = Log.create_logger('spider')
            logger.info('Spider running to crawl data by {}.'.format(args.spider))
            if args.spider == 'date':
                crawl_by_district()
            elif args.spider == 'district':
                pass


def crawl_by_district():
    logger = logging.getLogger('spider')

    # Read config
    start_dist, start_date, start_court = None, None, None
    start_info = Config.start
    logger.info('Start Reason: {}'.format(Config.search.reason.value))
    if hasattr(start_info, 'district') and start_info.district is not None:
        start_dist = start_info.district
        logger.info('Start District: {}'.format(start_dist))
    if hasattr(start_info, 'date') and start_info.date is not None:
        start_date = start_info.date
        logger.info('Start Date: {}'.format(start_date.strftime("%Y-%m-%d")))
    if hasattr(start_info, 'court') and start_info.court is not None:
        start_court = start_info.court
        logger.info('Start Court: {}'.format(start_court))

    max_retry = Config.config.max_retry
    data_file = open('./data/data_{}.txt'.format(datetime.now().strftime('%Y-%m-%d_%H-%M-%S')), 'a', encoding='utf-8')

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
                logger.info(dist)
                c1 = c.district(dist)

                # If time_interval is interrupted, continue from the start_date
                cur_date = start_date
                start_date = None

                # Variables for retry
                dist_success = False
                dist_retry = max_retry
                while not dist_success:
                    try:
                        for time_interval in spider.time_interval(condition=c1, start_date=cur_date):
                            logger.info('{0} {1} {2} {3}'.format(dist,
                                                                 time_interval[0].strftime('%Y-%m-%d'),
                                                                 time_interval[1].strftime('%Y-%m-%d'),
                                                                 time_interval[2]))
                            cur_date = time_interval[0]
                            time_success = False
                            time_retry = max_retry
                            index = 1
                            c2 = c1.date(time_interval[0], time_interval[1])

                            cur_court = start_court
                            start_court = None

                            while not time_success:
                                if time_interval[2] > 200:
                                    try:
                                        for court in spider.court(condition=c2, district=dist, start_court=cur_court):
                                            logger.info('{0} {1} {2} {3} {4} {5} {6}'.format(dist,
                                                                                             time_interval[0].strftime(
                                                                                                 '%Y-%m-%d'),
                                                                                             time_interval[1].strftime(
                                                                                                 '%Y-%m-%d'),
                                                                                             court[0], court[1],
                                                                                             court[2],
                                                                                             court[3]))
                                            if court[1] == 2:
                                                cur_court = court[0]
                                            court_success = False
                                            court_retry = max_retry
                                            index = 1
                                            c3 = c2.court(*court[0:3])
                                            while not court_success:
                                                try:
                                                    for item, idx in spider.content_list(
                                                            param=Parameter(param=str(c3),
                                                                            sess=s),
                                                            page=20, order='法院层级', direction='asc', index=index):
                                                        print(item, file=data_file)
                                                        index = idx
                                                    court_success = True
                                                except ExceptionList as e:
                                                    logger.error('Error when fetch content list: {0}'.format(str(e)))
                                                    court_retry -= 1
                                                    if court_retry <= 0:
                                                        s.switch_proxy()
                                                        court_retry = max_retry
                                        time_success = True
                                    except ExceptionList as e:
                                        logger.error('Error when fetch court: {0}'.format(str(e)))
                                        time_retry -= 1
                                        if time_retry <= 0:
                                            s.switch_proxy()
                                            time_retry = max_retry
                                else:
                                    try:
                                        for item, idx in spider.content_list(
                                                param=Parameter(param=str(c2),
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
                                    except ExceptionList as e:
                                        logger.error('Error when fetch content list: {0}'.format(str(e)))
                                        time_retry -= 1
                                        if time_retry <= 0:
                                            s.switch_proxy()
                                            time_retry = max_retry
                        dist_success = True
                    except ExceptionList as e:
                        logger.error('Error when fetch time interval: {0}'.format(str(e)))
                        dist_retry -= 1
                        if dist_retry <= 0:
                            s.switch_proxy()
                            dist_retry = max_retry
            total_success = True
        except ExceptionList as e:
            logger.error('Error when fetch dist information: {0}'.format(str(e)))
            s.switch_proxy()
    data_file.close()


def read_content_list():
    logger = logging.getLogger('downloader')
    total = 0
    available = 0
    data_dir = './data'
    database = RedisSet('spider')
    for data_file_name in os.listdir(data_dir):
        total_per_file = 0
        available_per_file = 0
        with open(os.path.join(data_dir, data_file_name), 'r', encoding='utf-8') as f:
            for line in f.readlines():
                try:
                    r = json.loads(line.replace("'", '"'))
                except json.JSONDecodeError:
                    print('JSON Decode Error: {}'.format(line))
                    continue
                if 'id' not in r:
                    print('ID not found: {}'.format(line))
                    continue
                case_id = r['id']
                total_per_file += 1
                if database.add(case_id) > 0:
                    available_per_file += 1
        logger.info('{0} / {1} from {2}'.format(available_per_file, total_per_file, data_file_name))
        total += total_per_file
        available += available_per_file
    return total, available


def download():
    s = Session()
    downloader = Downloader(sess=s)
    database = RedisSet('spider')
    logger = logging.getLogger('downloader')

    while database.count() > 0:
        doc_id = database.pop()
        try:
            downloader.download_doc(doc_id)
        except ExceptionList as e:
            logger.error('Error when downloading {0}: {1}'.format(doc_id, str(e)))
            database.add(doc_id)


# TODO: Crawl by date
# TODO: Downloader
# TODO: MultiTread Support --> Task Distributor, Content List Downloader, Document Downloader

if __name__ == '__main__':
    main()
