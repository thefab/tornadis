import tornado
import tornadis
import datetime
import random
import logging

BODY_SIZE = 1000000
BODY_TMP = ["%s" % random.randint(0, 9) for _ in range(0, BODY_SIZE)]
BODY = "".join(BODY_TMP)

logging.basicConfig(level=logging.CRITICAL)


@tornado.gen.coroutine
def setget_redis(client):
    reply1 = yield client.call("SET", "foo", BODY)
    if reply1 != "OK":
        # raise Exception('bad ok reply : %s', reply1)
        raise Exception('bad ok reply')
    reply2 = yield client.call("GET", "foo")
    if reply2 != BODY:
        # raise Exception('bad reply %i <> %i', len(reply2), len(BODY))
        raise Exception('bad reply')


@tornado.gen.coroutine
def multiple_setget_redis(pool):
    client = yield pool.get_connected_client()
    before = datetime.datetime.now()
    yield [setget_redis(client) for i in range(0, 1000)]
    after = datetime.datetime.now()
    print after - before
    pool.destroy()


def stop_loop(future):
    excep = future.exception()
    loop = tornado.ioloop.IOLoop.instance()
    loop.stop()
    if excep is not None:
        raise(excep)


pool = tornadis.ClientPool(max_size=5)
loop = tornado.ioloop.IOLoop.instance()
future = multiple_setget_redis(pool)
loop.add_future(future, stop_loop)
loop.start()
