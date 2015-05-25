import tornado
import tornadis
import logging
logging.basicConfig(level=logging.CRITICAL)


def ping_callback(result):
    if not isinstance(result, tornadis.ConnectionError):
        print result


@tornado.gen.coroutine
def main():
    client.async_call("PING", callback=ping_callback)
    yield tornado.gen.sleep(1)


loop = tornado.ioloop.IOLoop.instance()
client = tornadis.Client()
loop.run_sync(main)
