import tornado
import tornadis
import datetime


@tornado.gen.coroutine
def ping_redis(client):
    reply = yield client.call("PING")
    if reply != 'PONG':
        raise Exception('bad reply')


@tornado.gen.coroutine
def multiple_ping_redis(pool):
    client = yield pool.get_connected_client()
    before = datetime.datetime.now()
    for i in range(0, 10000):
        client.call("PING", discard_reply=True)
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
future = multiple_ping_redis(pool)
loop.add_future(future, stop_loop)
loop.start()
