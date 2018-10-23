import requests
import random
import time
import logging
from error import NetworkException

user_agent_list = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.81 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3497.81 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3497.81 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3497.81 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3497.81 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3497.81 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3497.81 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:62.0) Gecko/20100101 Firefox/62.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.140 Safari/537.36 Edge/17.17134',
    'Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) like Gecko'
]

PROXY = True


class Session:

    def __init__(self):
        self.session = requests.Session()
        if PROXY:
            self.proxy = self._get_proxy()
        self.TIMEOUT = 60

    @property
    def user_agent(self):
        return user_agent_list[random.randrange(0, len(user_agent_list))]

    @property
    def proxies(self):
        return {'http': 'http://' + self.proxy}

    def post(self, **kwargs):
        # 不能在这里重试，每当更换代理时都需要重新从头开始请求
        try:
            if PROXY:
                r = self.session.post(proxies=self.proxies, timeout=self.TIMEOUT, **kwargs)
            else:
                r = self.session.post(timeout=self.TIMEOUT, **kwargs)
            if r.status_code == 200:
                return r
            else:
                raise NetworkException('Status error: {0}.'.format(r.status_code))
        except requests.exceptions.Timeout:
            raise NetworkException('Connection timeout.')
        except requests.exceptions.ProxyError:
            raise NetworkException('Proxy connection refused.')
        except requests.exceptions.ConnectionError:
            raise NetworkException('Connection refused.')

    def get(self, **kwargs):
        try:
            if PROXY:
                r = self.session.get(proxies=self.proxies, timeout=self.TIMEOUT, **kwargs)
            else:
                r = self.session.get(timeout=self.TIMEOUT, **kwargs)
            if r.status_code == 200:
                return r
            else:
                raise NetworkException('Status error: {0}.'.format(r.status_code))
        except requests.exceptions.Timeout:
            raise NetworkException('Connection timeout.')
        except requests.exceptions.ProxyError:
            raise NetworkException('Proxy connection refused.')
        except requests.exceptions.ConnectionError:
            raise NetworkException('Connection refused.')

    @staticmethod
    def _get_proxy():
        while True:
            r = requests.get('http://127.0.0.1:5010/get/')
            if r.status_code != 200 or r.text == 'no proxy!':
                logging.error('No available proxy.')
                time.sleep(300)
            else:
                logging.info('Proxy changed to {0}'.format(r.text))
                return r.text

    @staticmethod
    def _del_proxy(proxy):
        requests.get('http://127.0.0.1:5010/delete/?proxy={0}'.format(proxy))

    def switch_proxy(self):
        if PROXY:
            self._del_proxy(self.proxy)
            self.proxy = self._get_proxy()
