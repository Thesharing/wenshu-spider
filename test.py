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
            param=Parameter(param=str(c.district('西藏自治区')),
                            sess=s)))
