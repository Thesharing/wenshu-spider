import os
import json
from dateutil import parser

Config = {
    'start': {
        'date': None,
        'district': None
    },
    'search': {
        'keyword': '*',
        'type': None
    },
    'condition': {
        '案由': None,
        '法院层级': None,
        '案件类型': '民事案件',
        '审判程序': None,
        '文书类型': None,
        '法院地域': None,
        '二级案由': '知识产权与竞争纠纷'
    },
    'config': {
        'maxRetry': 10,
        'proxy': True,
        'timeout': 60
    }
}

if os.path.isfile('config.json'):
    with open('config.json', 'r', encoding='utf-8') as f:
        Config = json.load(f)
        start_date = Config['start']['date']
        if start_date is not None:
            Config['start']['date'] = parser.parse(start_date)
else:
    with open('config.json', 'w', encoding='utf-8') as f:
        json.dump(Config, f, ensure_ascii=False, indent=4)
