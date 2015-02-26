import tornado
import tornadis
import logging
logging.basicConfig(level=logging.CRITICAL)

loop = tornado.ioloop.IOLoop.instance()


def connection_callback(future):
    exception = future.exception()
    if exception is None:
        print("We are connected to Redis")
    else:
        print("Error: %s" % exception)
    loop.stop()


client = tornadis.Client()
future = client.connect()
loop.add_future(future, connection_callback)
loop.start()
