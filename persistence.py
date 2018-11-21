import redis
import pymongo
import config


class RedisSet:

    def __init__(self, name: str):
        self.conn = redis.StrictRedis(host=config.Config.database.redis.host, port=config.Config.database.redis.port,
                                      decode_responses=True)
        self.name = name

    def add(self, values):
        return self.conn.sadd(self.name, values)

    def count(self):
        return self.conn.scard(self.name)

    def pop(self):
        return self.conn.spop(self.name)

    def remove(self, values):
        return self.conn.srem(self.name, values)

    def rand(self, number=None):
        if number:
            return self.conn.srandmember(self.name, number)
        else:
            return self.conn.srandmember(self.name)

    def is_member(self, value):
        return self.conn.sismember(self.name, value)

    def all(self):
        return self.conn.smembers(self.name)

    def flush_all(self):
        return self.conn.delete(self.name)


class MongoDB:

    def __init__(self, collection: str):
        client = pymongo.MongoClient(host=config.Config.database.mongodb.host, port=config.Config.database.mongodb.port)
        db = client[config.Config.database.mongodb.database]
        self.conn = db[collection]

    def insert(self, documents):
        if type(documents) is list:
            return self.conn.insert_many(documents)
        else:
            return self.conn.insert_one(documents)

    def remove(self, filter, all=False):
        if all:
            return self.conn.delete_many(filter=filter)
        else:
            return self.conn.delete_one(filter=filter)

    def update(self, filter, update, all=False):
        if all:
            return self.conn.update_many(filter=filter, update=update)
        else:
            return self.conn.update_one(filter=filter, update=update)

    def replace(self, filter, replacement):
        return self.conn.replace_one(filter=filter, replacement=replacement)

    def find(self, filter, all=False, **kwargs):
        if all:
            return self.conn.find(filter=filter, **kwargs)
        else:
            return self.conn.find_one(filter=filter, **kwargs)

    def all(self):
        return self.conn.find()

    def count(self, filter):
        return self.conn.count_documents(filter=filter)


def test_redis():
    conn = redis.StrictRedis(host=config.Config.database.redis.host, port=config.Config.database.redis.port,
                             decode_responses=True)
    conn.client_list()


def test_mongodb():
    client = pymongo.MongoClient(host=config.Config.database.mongodb.host, port=config.Config.database.mongodb.port,
                                 serverSelectionTimeoutMS=3000, connectTimeoutMS=3000)
    client.admin.command('ismaster')
