import tornado
import tornadis


@tornado.gen.coroutine
def pubsub():
    client = tornadis.Client()
    yield client.connect()
    yield client.pubsub_psubscribe("foo*")
    yield client.pubsub_subscribe("bar")
    while True:
        reply = yield client.pubsub_pop_message()
        print(reply)
        if reply[3] == "STOP":
            yield client.pubsub_punsubscribe("foo*")
            yield client.pubsub_unsubscribe("bar")
            break
    yield client.disconnect()


def stop_loop(future=None):
    excep = future.exception()
    if excep is not None:
        raise(excep)
    loop = tornado.ioloop.IOLoop.instance()
    loop.stop()


loop = tornado.ioloop.IOLoop.instance()
future = pubsub()
loop.add_future(future, stop_loop)
loop.start()
