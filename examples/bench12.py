import tornado
import tornadis
import datetime
import logging

logging.basicConfig(level=logging.CRITICAL)


@tornado.gen.coroutine
def multiple_ping_redis(pool):
    client = yield pool.get_connected_client()
    before = datetime.datetime.now()
    for i in range(0, 10000):
        reply = client.call2("PING")
        if not isinstance(reply, basestring):
            reply2 = yield reply
            if reply2 != "PONG":
                raise Exception('bad reply2')
        else:
            if reply != 'PONG':
                logging.warning("reply = %s" % reply)
                raise Exception('bad reply')
    after = datetime.datetime.now()
    print after - before
    pool.destroy()


def stop_loop(future):
    excep = future.exception()
    loop = tornado.ioloop.IOLoop.instance()
    loop.stop()
    if excep is not None:
        raise(excep)


pool = tornadis.ClientPool(max_size=100)
loop = tornado.ioloop.IOLoop.instance()
future = multiple_ping_redis(pool)
loop.add_future(future, stop_loop)
loop.start()
