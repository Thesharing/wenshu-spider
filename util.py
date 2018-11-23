import json
from datetime import datetime
from dateutil import parser
import logging
import os
from math import ceil

from persistence import RedisSet, test_redis


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


def merge_doc_and_split(number: int = 1):
    logging.basicConfig(format='[%(levelname)s] %(asctime)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S',
                        level=logging.INFO)

    data = dict()

    decode_error, id_not_found, duplicated = 0, 0, 0
    data_dir = './untracked/data'
    for data_file_name in os.listdir(data_dir):
        with open(os.path.join(data_dir, data_file_name), 'r', encoding='utf-8') as f:
            for line in f.readlines():
                line = line.strip()
                try:
                    r = json.loads(line.replace("'", '"'))
                except json.JSONDecodeError:
                    logging.error('JSON Decode Error {}.'.format(line))
                    decode_error += 1
                    continue
                if 'id' not in r or len(r['id']) <= 0:
                    logging.error('ID not found: {}.'.format(line))
                    id_not_found += 1
                    continue
                case_id = r['id']
                if case_id not in data:
                    data[case_id] = line
                else:
                    logging.warning('ID duplicated: {}.'.format(case_id))
                    duplicated += 1
    logging.info('Total: {0}, Available: {1}, JSON Decode Error: {2}, ID not found: {3}, Duplicated: {4}'.format(
        len(data) + decode_error + id_not_found + duplicated, len(data), decode_error, id_not_found, duplicated))

    result_dir = './untracked/split'

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
    test_redis()
    redis = RedisSet('failed')
    save_path = './untracked/FailedDocID.txt'
    with open(save_path, 'a', encoding='utf-8') as f:
        for item in redis.all():
            print(item, file=f)
    logging.info('Total {0} items are exported to {1}.'.format(redis.count(), save_path))


if __name__ == '__main__':
    export_failed_doc_id()
