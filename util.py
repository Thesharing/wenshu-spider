import json
from datetime import datetime
from dateutil import parser
import logging


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
