import datetime
import redis


c = redis.Redis()
c.ping()

before = datetime.datetime.now()
for i in range(0, 10000):
    result = c.ping()
    if not(result):
        raise Exception(result)
after = datetime.datetime.now()
print after - before
