from json import JSONDecodeError
from requests.exceptions import ChunkedEncodingError


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


ErrorList = (NetworkException, CheckCodeError, JSONDecodeError, KeyError, IndexError, ChunkedEncodingError)
