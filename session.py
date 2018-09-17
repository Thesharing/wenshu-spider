import requests
import random
import time

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


class Session:

    def __init__(self):
        self.session = requests.Session()

    @property
    def user_agent(self):
        return user_agent_list[random.randrange(0, len(user_agent_list))]

    def post(self, **kwargs):
        max_error = 100
        while max_error > 0:
            try:
                r = self.session.post(**kwargs)
                if r.status_code != 200:
                    print(r.status_code, 'Network Error, will wait 300s.')
                    time.sleep(300)
                else:
                    return r
            except:
                print('Network Error')
                time.sleep(10)
                max_error -= 1

    def get(self, **kwargs):
        max_error = 100
        while max_error > 0:
            try:
                r = self.session.get(**kwargs)
                if r.status_code != 200:
                    print(r.status_code, 'Network Error, will wait 300s.')
                    time.sleep(300)
                else:
                    return r
            except:
                print('Network Error')
                time.sleep(10)
                max_error -= 1
