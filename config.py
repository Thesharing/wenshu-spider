import os
import json
from dateutil import parser


class Nested:
    def __init__(self, structure):
        self.dict = structure

    def __new__(cls, structure):
        self = super(Nested, cls).__new__(cls)
        self.dict = structure
        if type(structure) is dict:
            self.__dict__ = {key: Nested(structure[key]) for key in structure}
        elif type(structure) is list:
            self = [Nested(item) for item in structure]
        else:
            self = structure
        return self

    def __str__(self):
        return str(self.dict)


Config = Nested({
    'start': {
        'date': None,
        'district': None,
        'court': None
    },
    'search': {
        'keyword': '*',
        'type': None,
        'reason': {
            'value': '知识产权与竞争纠纷',
            'level': 2
        },
        'court:': {
            'value': None,
            'level': 0,
            'indicator': False
        },
        'district': None
    },
    'condition': {
        '法院层级': None,
        '案件类型': '民事案件',
        '审判程序': None,
        '文书类型': None,
    },
    'config': {
        'max_retry': 10,
        'proxy': True,
        'timeout': 60
    }
})

if os.path.isfile('config.json'):
    with open('config.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        start_date = data['start']['date']
        if start_date is not None:
            data['start']['date'] = parser.parse(start_date)
        Config = Nested(data)
else:
    with open('config.json', 'w', encoding='utf-8') as f:
        json.dump(Config.data, f, ensure_ascii=False, indent=2)
