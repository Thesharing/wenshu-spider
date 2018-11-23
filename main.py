from parameter import Parameter
from session import Session, test_proxy
from condition import Condition
from spider import Spider
from downloader import Downloader
from error import ExceptionList
from datetime import datetime
from log import Log
from persistence import RedisSet, MongoDB, test_redis, test_mongodb
import config

from multiprocessing import Pool
import logging
import sys
import os
import json
import argparse
import time
import re


def main():
    if sys.version_info.major < 3 or sys.version_info.minor < 5:
        print('Python >= 3.5 is required, you are using {}.{}.'.format(sys.version_info.major, sys.version_info.minor))
        exit(1)

    # TODO: Specify the process and

    logging.basicConfig(format='[%(levelname)s] %(asctime)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S',
                        level=logging.INFO)

    parser = argparse.ArgumentParser(description='Court Spider')
    parser.add_argument('-s', '--spider', nargs='?', choices=['date', 'district'], const='date',
                        help='Start a spider to crawl data by date or by district')
    parser.add_argument('-d', '--downloader', nargs='?', choices=['read', 'download'], const='download',
                        help='Start a downloader')
    parser.add_argument('-c', '--config', nargs='?', help='Specify the filename of config')
    args = parser.parse_args()

    # Specify the filename of config
    if args.config is not None:
        logging.info('Config read from {0}.'.format(args.config))
        config.read_config(args.config)
    else:
        logging.info('Config read from config.json.')

    if args.spider is None:
        if args.downloader is None:

            # Run multiprocess
            logging.info('Multiprocess mode on.')
            test_redis()
            test_mongodb()
            logging.info(test_proxy())

            pool = Pool(processes=config.Config.multiprocess.total)

            for i in range(config.Config.multiprocess.spider):
                pool.apply_async(crawl_by_district)

            for i in range(config.Config.multiprocess.downloader):
                pool.apply_async(download)

            pool.close()
            pool.join()

        else:

            # Run single instance of downloader
            test_redis()
            test_mongodb()
            logging.info(test_proxy())

            if args.downloader == 'read':
                read_content_list()
            elif args.downloader == 'download':
                download()

    if args.spider is not None:
        if args.downloader is not None:

            logging.error('Choose one from spider or downloader, not both.')
            parser.print_help()
            exit(1)
        else:

            # Run single instance of spider
            if args.spider == 'date':
                crawl_by_district()
            elif args.spider == 'district':
                pass


def crawl_by_district():
    logger = Log.create_logger('spider')
    logger.info('Spider running to crawl data by date.')

    # Read config
    start_dist, start_date, start_court = None, None, None
    start_info = config.Config.start
    logger.info('Start Reason: {}'.format(config.Config.search.reason.value))
    if hasattr(start_info, 'district') and start_info.district is not None:
        start_dist = start_info.district
        logger.info('Start District: {}'.format(start_dist))
    if hasattr(start_info, 'date') and start_info.date is not None:
        start_date = start_info.date
        logger.info('Start Date: {}'.format(start_date.strftime("%Y-%m-%d")))
    if hasattr(start_info, 'court') and start_info.court is not None:
        start_court = start_info.court
        logger.info('Start Court: {}'.format(start_court))

    max_retry = config.Config.config.max_retry
    data_file = open('./data/data_{}.txt'.format(datetime.now().strftime('%Y-%m-%d_%H-%M-%S')), 'a', encoding='utf-8')

    s = Session()
    c = Condition()
    spider = Spider(sess=s)

    while True:
        try:
            if start_dist is not None:
                start = False
            else:
                start = True

            # Log the distribution of district
            with open('district_list.txt', 'w', encoding='utf-8') as f:
                district_list = list(spider.district(condition=c))
                if len(district_list) <= 0:
                    logger.error('No district found, maybe wrong search condition input.')
                    exit(-1)
                print(json.dumps(district_list, ensure_ascii=False), file=f)

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
                dist_retry = max_retry
                while True:

                    # First fetch time interval
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

                            while True:

                                # If count of that day > 200, fetch court interval
                                if time_interval[2] > 200:
                                    try:
                                        for court in spider.court(condition=c2, district=dist, start_court=cur_court):
                                            logger.info('{0} {1} {2} {3} {4} {5} '
                                                        '{6}'.format(dist,
                                                                     time_interval[0].strftime('%Y-%m-%d'),
                                                                     time_interval[1].strftime('%Y-%m-%d'),
                                                                     court[0], court[1], court[2], court[3]))
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
                                                        index = min(idx + 1, 10)
                                                    court_success = True
                                                except ExceptionList as e:
                                                    logger.error('Error when fetch content list: {0}'.format(str(e)))
                                                    court_retry -= 1
                                                    if court_retry <= 0:
                                                        s.switch_proxy()
                                                        court_retry = max_retry
                                        break
                                    except ExceptionList as e:
                                        logger.error('Error when fetch court: {0}'.format(str(e)))
                                        time_retry -= 1
                                        if time_retry <= 0:
                                            s.switch_proxy()
                                            time_retry = max_retry

                                # If count of that day < 200, directly fetch all the doc_id
                                else:
                                    try:
                                        for item, idx in spider.content_list(
                                                param=Parameter(param=str(c2),
                                                                sess=s),
                                                page=20, order='法院层级', direction='asc', index=index):
                                            print(item, file=data_file)
                                            index = min(idx + 1, 10)
                                        break
                                    except ExceptionList as e:
                                        logger.error('Error when fetch content list: {0}'.format(str(e)))
                                        time_retry -= 1
                                        if time_retry <= 0:
                                            s.switch_proxy()
                                            time_retry = max_retry
                        break
                    except ExceptionList as e:
                        logger.error('Error when fetch time interval: {0}'.format(str(e)))
                        dist_retry -= 1
                        if dist_retry <= 0:
                            s.switch_proxy()
                            dist_retry = max_retry
            break
        except ExceptionList as e:
            logger.error('Error when fetch dist information: {0}'.format(str(e)))
            s.switch_proxy()
    data_file.close()


def read_content_list():
    logger = Log.create_logger('downloader')
    logger.info('Downloader reading contents from local files.')
    total = 0
    available = 0
    data_dir = './data'
    pattern = re.compile(r"{'id': '(.+?)',")
    database = RedisSet('spider')

    for data_file_name in os.listdir(data_dir):
        total_per_file = 0
        available_per_file = 0
        with open(os.path.join(data_dir, data_file_name), 'r', encoding='utf-8') as f:
            for line in f.readlines():
                line = line.strip()
                if len(line) > 0:
                    res = pattern.findall(line)
                    if len(res) > 0:
                        case_id = res[0]
                        total_per_file += 1
                        if database.add(case_id) > 0:
                            available_per_file += 1
                    else:
                        logging.info('ID not found: {0}.'.format(line))
        logger.info('Retrieve {0} / {1} from {2}.'.format(available_per_file, total_per_file, data_file_name))
        total += total_per_file
        available += available_per_file

    logger.info('Data retrieved from local file: {} total, {} available.'.format(total, available))
    return total, available


def download():
    logger = Log.create_logger('downloader')
    logger.info('Downloader {0} running.'.format(os.getpid()))
    s = Session()

    redis = RedisSet('spider')
    finish = RedisSet('finish')
    progress = RedisSet('progress')
    failed = RedisSet('failed')

    mongo = MongoDB('文书')
    downloader = Downloader(sess=s, db=mongo)

    def work(doc_id):
        doc_retry = 3
        time_retry = config.Config.config.max_retry
        logger.info('Document {0} start.'.format(doc_id))
        while True:
            time.sleep(1)

            try:
                downloader.download_doc(doc_id)
                progress.remove(doc_id)
                finish.add(doc_id)
                logger.info('Document {0} finished.'.format(doc_id))
                break

            except ExceptionList as e:
                logger.error('Error when downloading {0}: {1}'.format(doc_id, str(e)))
                time_retry -= 1

                # Retry once more
                if time_retry <= 0:
                    doc_retry -= 1
                    s.switch_proxy()
                    time_retry = config.Config.config.max_retry

                # Fail too many times, try another one
                if doc_retry <= 0:
                    logger.critical('Max error when downloading {0}: {1}'.format(doc_id, str(e)))
                    progress.remove(doc_id)
                    failed.add(doc_id)
                    break

    # Put all item_id in progress in last session back to the waiting pool
    idx = 0
    while progress.count() > 0:
        item_id = progress.pop()
        idx += 1
        redis.add(item_id)

    if idx > 0:
        logger.info('{0} items in last session are recovered.'.format(idx))

    logger.info('Total {0} items ongoing.'.format(redis.count()))

    while redis.count() > 0:
        item_id = redis.pop()
        progress.add(item_id)
        work(item_id)


if __name__ == '__main__':
    main()
    # TODO: Crawl by date
    # TODO: Downloader
    # TODO: MultiTread Support --> Task Distributor, Content List Downloader, Document Downloader
    # TODO: Extractor
