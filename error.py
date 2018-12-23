from json import JSONDecodeError
from requests.exceptions import ChunkedEncodingError, RequestException
from execjs._exceptions import ProgramError


class SpiderException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value


class NetworkException(SpiderException):

    def __init__(self, value):
        super(NetworkException, self).__init__(value)
        self.msg = 'Network Error'


class CheckCodeError(SpiderException):

    def __init__(self, value):
        super(SpiderException, self).__init__(value)
        self.msg = 'CheckCode Error'


class NullContentError(SpiderException):

    def __init__(self, value):
        super(NullContentError, self).__init__(value)
        self.msg = 'Null Content Error'


class DocNotFoundError(SpiderException):

    def __init__(self, value):
        super(DocNotFoundError, self).__init__(value)
        self.msg = 'Doc not found'


ExceptionList = (NetworkException, CheckCodeError, JSONDecodeError,
                 NullContentError, KeyError, IndexError, TypeError,
                 ChunkedEncodingError, RequestException, ProgramError,
                 UnicodeEncodeError, UnicodeDecodeError)
