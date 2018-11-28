import os
from abc import abstractmethod

import redis
import pymongo

import config


class Database:
    def __init__(self, name: str, db_type):
        self.name = name
        self.type = db_type

    @abstractmethod
    def count(self):
        pass


class RedisSet(Database):

    def __init__(self, name: str):
        super(RedisSet, self).__init__(name, 'Redis')
        self.conn = redis.StrictRedis(host=config.Config.database.redis.host, port=config.Config.database.redis.port,
                                      decode_responses=True)

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


class MongoDB(Database):

    def __init__(self, collection: str):
        super(MongoDB, self).__init__(collection, 'MongoDB')
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

    def count(self, filter=None):
        if filter is None:
            return self.conn.count_documents(filter={})
        else:
            return self.conn.count_documents(filter=filter)


class LocalFile(Database):
    def __init__(self, file_path: str, file_type=None):
        super(LocalFile, self).__init__(os.path.basename(file_path), 'LocalFile')
        self.file_path = file_path
        self.file_type = file_type

    def count(self):
        if os.path.isdir(self.file_path):
            if self.file_type:
                return len([name for name in os.listdir(self.file_path) if
                            os.path.isfile(os.path.join(self.file_path, name)) and os.path.splitext(
                                name) == self.file_type])
            else:
                return len([name for name in os.listdir(self.file_path)
                            if os.path.isfile(os.path.join(self.file_path, name))])
        else:
            return 0


def test_redis():
    conn = redis.StrictRedis(host=config.Config.database.redis.host, port=config.Config.database.redis.port,
                             decode_responses=True)
    conn.client_list()


def test_mongodb():
    client = pymongo.MongoClient(host=config.Config.database.mongodb.host, port=config.Config.database.mongodb.port,
                                 serverSelectionTimeoutMS=3000, connectTimeoutMS=3000)
    client.admin.command('ismaster')
