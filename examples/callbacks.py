import tornado
import tornadis
import logging
logging.basicConfig(level=logging.CRITICAL)

loop = tornado.ioloop.IOLoop.instance()
client = tornadis.Client()


def ping_callback(ping_future):
    exception = ping_future.exception()
    if exception is None:
        print("Command result: %s" % ping_future.result())
    else:
        print("Error: %s" % exception)
    loop.stop()


def connection_callback(connect_future):
    exception = connect_future.exception()
    if exception is None:
        print("We are connected to Redis")
        ping_future = client.call("PING")
        loop.add_future(ping_future, ping_callback)
    else:
        print("Error: %s" % exception)


connect_future = client.connect()
loop.add_future(connect_future, connection_callback)
loop.start()
