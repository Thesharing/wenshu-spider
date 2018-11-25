from json import JSONDecodeError
from requests.exceptions import ChunkedEncodingError, RequestException
from execjs._exceptions import ProgramError


class NetworkException(Exception):

    def __init__(self, value):
        self.value = value
        self.msg = 'Network Error'

    def __str__(self):
        return self.value


class CheckCodeError(Exception):

    def __init__(self, value):
        self.value = value
        self.msg = 'CheckCode Error'

    def __str__(self):
        return self.value


class NullContentError(Exception):

    def __init__(self, value):
        self.value = value
        self.msg = 'Null Content Error'

    def __str__(self):
        return self.value


ExceptionList = (NetworkException, CheckCodeError, JSONDecodeError,
                 NullContentError, KeyError, IndexError, TypeError,
                 ChunkedEncodingError, RequestException, ProgramError,
                 UnicodeEncodeError, UnicodeDecodeError)
