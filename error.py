class NetworkException(Exception):

    def __init__(self, value):
        self.value = value
        self.msg = 'Network Error'

    def __str__(self):
        return self.value
