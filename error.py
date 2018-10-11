from json import JSONDecodeError


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


error_list = (NetworkException, CheckCodeError, JSONDecodeError, KeyError, IndexError)
