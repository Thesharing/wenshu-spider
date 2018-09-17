from parameter import Parameter
from session import Session
from config import Config
from spider import Spider
from datetime import datetime

if __name__ == '__main__':

    s = Session()
    c = Config()
    # parameter = Parameter(param=str(c), sess=s)
    spider = Spider(sess=s)
    # page: 每页几条; order: 排序标准; direction: 顺序 (asc - 正序 desc - 倒序)
    print(spider.tree_content(
            param=Parameter(param=str(c.district('西藏自治区').date(datetime(1991, 1, 1), datetime(2018, 9, 15))),
                            sess=s)))
    for i in spider.content_list(param=Parameter(param=
                                              str(c.district('西藏自治区').
                                                  date(datetime(1991, 1, 1), datetime(2018, 9, 15)))),
                              page=20, order='法院层级', direction='asc'):
        print(i)
