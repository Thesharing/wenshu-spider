import os
import re
import sys
import time
import json
import logging
import argparse
from datetime import datetime
from multiprocessing import Pool

import pymongo

import config
from log import Log
from spider import Spider
from util import git_date
from parameter import Parameter
from error import ExceptionList
from condition import Condition
from downloader import Downloader
from session import Session, test_proxy
from notifier import WeChatNotifier, EmailNotifier
from persistence import RedisSet, MongoDB, LocalFile, test_redis, test_mongodb


def main():
    if sys.version_info.major < 3 or sys.version_info.minor < 5:
        print('Python >= 3.5 is required, you are using {}.{}.'.format(sys.version_info.major, sys.version_info.minor))
        exit(1)

    logging.basicConfig(format='[%(levelname)s] %(asctime)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S',
                        level=logging.INFO)

    parser = argparse.ArgumentParser(description='Court Spider')
    sub_parser = parser.add_subparsers(description='Functions of Court Spider', dest='function')
    parser_spider = sub_parser.add_parser('spider', help='Start a spider', aliases=['s'])
    group_spider = parser_spider.add_mutually_exclusive_group()
    group_spider.add_argument('--date', action='store_const', dest='type', const='date',
                              help='Crawl data by date')
    group_spider.add_argument('--district', action='store_const', dest='type', const='district',
                              help='Crawl data by district')
    parser_spider.set_defaults(type='district')
    parser_downloader = sub_parser.add_parser('downloader', help='Start a downloader', aliases=['d'])
    group_downloader = parser_downloader.add_mutually_exclusive_group()
    group_downloader.add_argument('--clean', action='store_const', dest='type', const='clean',
                                  help='Delete all data in Redis before read')
    group_downloader.add_argument('--read', action='store_const', dest='type', const='read',
                                  help='Read data from files')
    group_downloader.add_argument('--download', action='store_const', dest='type', const='download',
                                  help='Download docs')
    parser_downloader.set_defaults(type='download')
    parser_notifier = sub_parser.add_parser('notifier', help='Start a notifier', aliases=['n'])
    parser.add_argument('-c', '--config', nargs='?', help='Specify the filename of config')
    args = parser.parse_args()

    logging.info('Version: {}.'.format(git_date()))

    # Specify the filename of config
    if args.config is not None:
        logging.info('Config: {0}.'.format(args.config))
        config.read_config(args.config)
    else:
        logging.info('Config: config.json.')

    if args.function is None:
        # Run multiprocess
        logging.info('Multiprocess Mode: On.')
        test_redis()
        test_mongodb()
        logging.info(test_proxy())

        pool = Pool(processes=config.Config.multiprocess.total)

        for i in range(config.Config.multiprocess.spider):
            pool.apply_async(crawl_by_district)

        for i in range(config.Config.multiprocess.downloader):
            pool.apply_async(download)

        for i in range(config.Config.multiprocess.notifier):
            pool.apply_async(notify)

        logging.info('Processes: Total {} | Spider {} | Downloader {} | Notifier {}'.format(
            config.Config.multiprocess.total, config.Config.multiprocess.spider,
            config.Config.multiprocess.downloader, config.Config.multiprocess.notifier))

        pool.close()
        pool.join()

    elif args.function == 'spider' or args.function == 's':
        # Run single instance of spider
        if args.type == 'date':
            pass
        elif args.type == 'district':
            crawl_by_district()

    elif args.function == 'downloader' or args.function == 'd':
        # Run single instance of downloader
        test_redis()
        if args.type == 'read':
            read_content_list()
        elif args.type == 'clean':
            clean_content_list()
        elif args.type == 'download':
            test_mongodb()
            logging.info(test_proxy())
            download()

    elif args.function == 'notifier' or args.function == 'n':
        # Run single instance of notifier:
        notify()


def crawl_by_district():
    logger = Log.create_logger('spider')
    logger.info('Spider running to crawl data by district.')

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
                                            court_retry = max_retry
                                            index = 1
                                            c3 = c2.court(*court[0:3])

                                            while True:
                                                try:
                                                    for item, idx in spider.content_list(
                                                            param=Parameter(param=str(c3),
                                                                            sess=s),
                                                            page=20, order='法院层级', direction='asc', index=index):
                                                        print(item, file=data_file)
                                                        index = min(idx + 1, 10)
                                                    break
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


def clean_content_list():
    logger = Log.create_logger('downloader')
    database = RedisSet('spider')
    database.flush_all()
    logger.info('All DocID in redis has been deleted.')


def read_content_list():
    logger = Log.create_logger('downloader')
    total = 0
    available = 0
    duplicate = 0
    data_dir = './temp'
    logger.info('Downloader reading contents from local files in {0}.'.format(data_dir))
    pattern = re.compile(r"{'id': '(.+?)',")
    database = RedisSet('spider')
    mongo = MongoDB('文书')
    index = [('文书ID', pymongo.HASHED)]
    mongo.create_index(index)

    for data_file_name in os.listdir(data_dir):
        if data_file_name[-4:] != '.txt':
            continue
        total_per_file = 0
        available_per_file = 0
        duplicate_per_file = 0
        with open(os.path.join(data_dir, data_file_name), 'r', encoding='utf-8') as f:
            for line in f.readlines():
                line = line.strip()
                if len(line) > 0:
                    res = pattern.findall(line)
                    if len(res) > 0:
                        case_id = res[0]
                        total_per_file += 1
                        if mongo.count({'文书ID': case_id}, hint=index) <= 0:
                            if database.add(case_id) > 0:
                                available_per_file += 1
                        else:
                            duplicate_per_file += 1
                    else:
                        logging.info('ID not found: {0}.'.format(line))
        logger.info(
            'Retrieve {0} / {1} from {2}, {3} duplicated in MongoDB.'.format(
                available_per_file, total_per_file, data_file_name, duplicate_per_file))
        total += total_per_file
        available += available_per_file
        duplicate += duplicate_per_file

    logger.info('Data retrieved from local file: {} total, {} available, {} duplicated in MongoDB.'.format(
        total, available, duplicate))
    logger.info('Total {} items in redis database.'.format(database.count()))
    return total, available, duplicate


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

    idx = 0
    while failed.count() > 0:
        item_id = failed.pop()
        idx += 1
        redis.add(item_id)

    if idx > 0:
        logger.info('{0} items failed in past are recovered.'.format(idx))

    logger.info('Total {0} items ongoing.'.format(redis.count()))

    while redis.count() > 0:
        item_id = redis.pop()
        progress.add(item_id)
        work(item_id)


def notify():
    logger = Log.create_logger('notifier')
    logger.info('Notifier {0} running'.format(os.getpid()))

    databases = [RedisSet('spider'), RedisSet('finish'), RedisSet('progress'), RedisSet('failed'), MongoDB('文书'),
                 LocalFile('./download')]

    if config.Config.notifier.type == 'wechat':
        notifier = WeChatNotifier(databases=databases, ongoing='spider', saved='文书',
                                  period=config.Config.notifier.period, receiver=config.Config.notifier.wechat.receiver,
                                  scan_in_cmd=config.Config.notifier.wechat.cmd)
    elif config.Config.notifier.type == 'email':
        notifier = EmailNotifier(databases=databases, ongoing='spider', saved='文书',
                                 period=config.Config.notifier.period, sender=config.Config.notifier.email.sender,
                                 password=config.Config.notifier.email.password,
                                 server_addr=config.Config.notifier.email.server_addr,
                                 ssl=config.Config.notifier.email.ssl,
                                 receiver=config.Config.notifier.email.receiver)
    else:
        logger.error('Config error: not supported notifier type {0}'.format(config.Config.notifier.type))
        return
    notifier.run()


if __name__ == '__main__':
    main()
    # TODO: Crawl by date
    # TODO: Downloader
    # TODO: MultiTread Support --> Task Distributor, Content List Downloader, Document Downloader
    # TODO: Extractor
