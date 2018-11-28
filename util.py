import json
import logging
import os
import re
import subprocess
import sys

from datetime import datetime
from decimal import Decimal
from datetime import date
from dateutil import parser
from math import ceil


class CustomJsonEncoder(json.JSONEncoder):
    def __init__(self, *args, **kwargs):
        super(CustomJsonEncoder, self).__init__(ensure_ascii=False, *args, **kwargs)

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime("%Y-%m-%d")
        return super(CustomJsonEncoder, self).default(obj)


class CustomJsonDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(self, object_hook=self.object_hook, *args, **kwargs)

    @staticmethod
    def object_hook(obj):
        try:
            if obj is not None and 'date' in obj:
                obj['date'] = parser.parse(obj['date'])
        except (ValueError, TypeError) as e:
            logging.error('JSON Decode error: {}'.format(str(e)))
        finally:
            return obj


def encode_json(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, date):
        return obj.strftime("%Y-%m-%d")
    elif isinstance(obj, datetime):
        return obj.strftime("%Y-%m-%d")
    raise TypeError


def git_date():
    p = subprocess.Popen(["git", "log", "-1", "--format='%aI %s'"], stdout=subprocess.PIPE)
    out, err = p.communicate()
    return out.decode(sys.getdefaultencoding()).strip()[1:-1]


def merge_doc_and_split(number: int = 1):
    logging.basicConfig(format='[%(levelname)s] %(asctime)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S',
                        level=logging.INFO)

    data = dict()
    id_not_found, duplicated = 0, 0
    data_dir = './temp/data'
    pattern = re.compile(r"{'id': '(.+?)',")

    for data_file_name in os.listdir(data_dir):
        if data_file_name[-4:] != '.txt':
            continue
        with open(os.path.join(data_dir, data_file_name), 'r', encoding='utf-8') as f:
            for line in f.readlines():
                line = line.strip()
                if len(line) > 0:
                    res = pattern.findall(line)
                    if len(res) > 0:
                        case_id = res[0]
                        if case_id not in data:
                            data[case_id] = line
                        else:
                            logging.warning('ID duplicated: {}.'.format(case_id))
                            duplicated += 1
                    else:
                        logging.info('ID not found: {0}.'.format(line))
                        id_not_found += 1
    logging.info('Total: {0}, Available: {1}, ID not found: {2}, Duplicated: {3}'.format(
        len(data) + id_not_found + duplicated, len(data), id_not_found, duplicated))

    result_dir = './temp/split'
    if not os.path.isdir(result_dir):
        os.mkdir(result_dir)

    piece_size = ceil(len(data) / number)
    data = list(data.values())

    for piece_idx in range(number):
        with open(os.path.join(result_dir, '{}.txt'.format(piece_idx + 1)), 'w', encoding='utf-8') as f:
            for item in data[piece_idx * piece_size: (piece_idx + 1) * piece_size]:
                print(item, file=f)
        piece_idx += 1
        logging.info('Finish output of piece {}.'.format(piece_idx))
    logging.info('Finish.')


def export_failed_doc_id():
    from persistence import RedisSet, test_redis
    test_redis()
    redis = RedisSet('failed')
    save_path = './temp/FailedDocID.txt'
    with open(save_path, 'a', encoding='utf-8') as f:
        for item in redis.all():
            print(item, file=f)
    logging.info('Total {0} items are exported to {1}.'.format(redis.count(), save_path))


if __name__ == '__main__':
    export_failed_doc_id()
