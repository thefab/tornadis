import tornado
import tornadis
import logging
logging.basicConfig(level=logging.CRITICAL)


@tornado.gen.coroutine
def talk_to_redis():
    result = yield client.call("PING")
    if not isinstance(result, tornadis.TornadisException):
        print "Result: %s" % result


loop = tornado.ioloop.IOLoop.instance()
client = tornadis.Client()
loop.run_sync(talk_to_redis)
