import random
import execjs
from urllib import parse
from session import Session

from error import NetworkException

class Parameter:

    def __init__(self, param: str, sess: Session):
        self.sess = sess
        self.param = param

        with open('./js/vl5x.js') as f:
            js = f.read()
            self.js_vl5x = execjs.compile(js)

        self.guid = self._guid()
        self.number = self._number()
        self.vjkl5 = self._vjkl5(param)
        self.vl5x = self._vl5x()

    def refresh(self):
        self.guid = self._guid()
        self.number = self._number()

    @staticmethod
    def _guid():
        """
        生成GUID
        """
        def create_guid():
            return str(hex((int(((1 + random.random()) * 0x10000)) | 0)))[3:]

        return '{}{}-{}-{}{}-{}{}{}'.format(
            create_guid(), create_guid(),
            create_guid(), create_guid(),
            create_guid(), create_guid(),
            create_guid(), create_guid()
        )

    def _number(self):
        """
        获取Number
        """
        code_url = "http://wenshu.court.gov.cn/ValiCode/GetCode"
        data = {
            'guid': self.guid
        }
        headers = {
            'Host': 'wenshu.court.gov.cn',
            'Origin': 'http://wenshu.court.gov.cn',
            'Referer': 'http://wenshu.court.gov.cn/',
            'X-Requested-With': 'XMLHttpRequest',
            'User-Agent': self.sess.user_agent
        }
        r = self.sess.post(url=code_url, data=data, headers=headers)
        return r.text

    def _vjkl5(self, param):
        """
        获取Cookies中的vjkl5
        """
        url = "http://wenshu.court.gov.cn/list/list/?sorttype=1&number=" + self.number \
              + "&guid=" + self.guid \
              + "&conditions=searchWord+QWJS+++" + parse.quote(param)
        # referer = url
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh;q=0.8",
            "Host": "wenshu.court.gov.cn",
            "Proxy-Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": self.sess.user_agent
        }
        retry_time = 5
        while retry_time > 0:
            r = self.sess.get(url=url, headers=headers)
            try:
                vjkl5 = r.cookies["vjkl5"]
                return vjkl5
            except:
                retry_time -= 1
        raise NetworkException('Cannot find vjkl5 in cookies.')

    def _vl5x(self):
        return self.js_vl5x.call('GetVl5x', self.vjkl5)
