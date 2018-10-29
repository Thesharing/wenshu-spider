import logging
from datetime import datetime


class Log:
    @staticmethod
    def create_logger(name: str):
        logger = logging.getLogger(name)
        logger.propagate = False
        formatter = logging.Formatter(fmt='[%(levelname)s] %(asctime)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        file_handler = logging.FileHandler(
            './log/log_{0}_{1}.txt'.format(datetime.now().strftime('%Y-%m-%d_%H-%M-%S'), name),
            encoding='utf-8', mode='a')
        file_handler.setFormatter(formatter)
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)
        logger.setLevel(logging.INFO)
        return logger
