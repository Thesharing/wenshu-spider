from parameter import Parameter
from session import Session
from config import Config
from spider import Spider
from error import NetworkException, CheckCodeError
from json import JSONDecodeError

from datetime import datetime
import logging

if __name__ == '__main__':

    logging.basicConfig(format='[%(levelname)s] %(asctime)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S',
                        level=logging.INFO)
    s = Session()
    c = Config()
    spider = Spider(sess=s)
    data_log = open('./log/data-{}.txt'.format(datetime.now().strftime('%Y-%m-%d %H-%M-%S')), 'w', encoding='utf-8')
    for dist in spider.district(config=c):
        logging.info(dist)
        c1 = c.district(dist)
        dist_success = False
        first_retry_time = 5
        while not dist_success:
            try:
                for d in spider.time_interval(config=c1):
                    logging.info('{0} {1} {2}'.format(dist, d[0].strftime('%Y-%m-%d'), d[1].strftime('%Y-%m-%d')))
                    time_success = False
                    second_retry_time = 5
                    while not time_success:
                        try:
                            for item in spider.content_list(param=Parameter(param=str(c1.date(d[0], d[1])), sess=s),
                                                            page=20, order='法院层级', direction='asc'):
                                print(item, file=data_log)
                                # print(item['id'], item['name'])
                                # try:
                                #     spider.download_doc(item['id'])
                                # except:
                                #     print(item['id'], file=error_log)
                            time_success = True
                        except (NetworkException, CheckCodeError, JSONDecodeError) as e:
                            logging.error('Error when fetch content list: {0}'.format(str(e)))
                            second_retry_time -= 1
                            if second_retry_time <= 0:
                                s.switch_proxy()
                                second_retry_time = 5
                dist_success = True
            except (NetworkException, CheckCodeError, JSONDecodeError) as e:
                logging.error('Error when fetch time interval: {0}'.format(str(e)))
                first_retry_time -= 1
                if first_retry_time <= 0:
                    s.switch_proxy()
                    first_retry_time = 5
    data_log.close()
