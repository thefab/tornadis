import tornado
import tornadis
import logging
logging.basicConfig(level=logging.CRITICAL)

loop = tornado.ioloop.IOLoop.instance()
client = tornadis.Client()


def callback(future):
    exception = future.exception()
    if exception is not None:
        raise exception
    loop.stop()


@tornado.gen.coroutine
def talk_to_redis():
    yield client.connect()
    result = yield client.call("PING")
    print "Result: %s" % result


connect_future = client.connect()
main_future = talk_to_redis()
loop.add_future(main_future, callback)
loop.start()
