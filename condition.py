from datetime import datetime
from copy import deepcopy
from config import Config


class Condition:
    def __init__(self):
        # 构造检索条件

        self.keyword = Config.search.keyword
        self.search_type = Config.search.type

        self.reason_value = Config.search.reason.value
        self.reason_level = Config.search.reason.level
        self.reason_list = ['', '案由', '二级案由', '三级案由', '四级案由', '五级案由']

        self.court_value = Config.search.court.value
        self.court_level = Config.search.court.level
        self.court_indicator = Config.search.court.indicator
        self.court_list = ['', '高级法院', '中级法院', '基层法院']

        self.district_value = Config.search.district
        self.params = Config.condition.dict

        self.start_date = None
        self.end_date = None

        # # 检索关键词
        # keyword = '*'  # 空关键字 ==> '*'
        # # 检索类型
        # search_type = None  # ['全文检索', '首部', '事实', '理由', '判决结果', '尾部']
        #
        # # 其他检索条件
        # params = dict()
        # params['案由'] = None  # ['刑事案由', '民事案由', '行政案由', '赔偿案由']
        # params['法院层级'] = None  # ['最高法院', '高级法院', '中级法院', '基层法院']
        # params['案件类型'] = '民事案件'  # ['刑事案件', '民事案件', '行政案件', '赔偿案件', '执行案件']
        # params['审判程序'] = None  # ['全部', '一审', '二审', '再审', '复核', '刑罚变重', '再审审查与审判监督', '其他']
        # params['文书类型'] = None  # ['全部', '裁判书', '调解书', '决定书', '通知书', '批复', '答复', '函', '令', '其他']
        # params['法院地域'] = None  # 法院地域需要二次获取，判断哪些省份的法院有数据
        # params['二级案由'] = '知识产权与竞争纠纷'

    @property
    def param_list(self):
        # 构造参数列表
        param_list = list()
        if self.search_type is not None:
            param_list.append("{0}:{1}".format(self.search_type, self.keyword))
        if self.reason_value is not None and self.reason_level > 0:
            param_list.append("{0}:{1}".format(self.reason_list[self.reason_level], self.reason_value))
        if self.court_value is not None and self.court_level > 1:
            param_list.append("{0}:{1}".format(self.court_list[self.court_level], self.court_value))
        if self.court_indicator:
            param_list.append("法院层级:{0}".format(self.court_list[self.court_level]))
        if self.district_value is not None:
            param_list.append("法院地域:{0}".format(self.district_value))
        if self.start_date is not None and self.end_date is not None:
            param_list.append(
                '裁判日期:{0} TO {1}'.format(self.start_date.strftime('%Y-%m-%d'), self.end_date.strftime('%Y-%m-%d')))
        for name, value in self.params.items():
            if value is not None:
                param_list.append("{0}:{1}".format(name, value))

        return param_list

    def date(self, start_date: datetime, end_date: datetime) -> 'Condition':
        """
        针对日期返回param字符串
        """
        c = deepcopy(self)
        c.start_date = start_date
        c.end_date = end_date
        return c

    def district(self, district: str) -> 'Condition':
        c = deepcopy(self)
        c.district_value = district
        return c

    def court(self, court_value: str, court_level: int, court_indicator: bool) -> 'Condition':
        c = deepcopy(self)
        c.court_level = court_level
        c.court_value = court_value
        c.court_indicator = court_indicator
        return c

    def __str__(self):
        return ','.join(self.param_list)

    def __repr__(self):
        return str(self)
