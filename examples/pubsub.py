import tornado
import tornadis


@tornado.gen.coroutine
def pubsub():
    client = tornadis.Client()
    yield client.connect()
    reply = yield client.call("PSUBSCRIBE", "*")
    print(reply)
    while True:
        reply = yield client.pop_message()
        print(reply)


def stop_loop(future):
    loop = tornado.ioloop.IOLoop.instance()
    loop.stop()


loop = tornado.ioloop.IOLoop.instance()
future = pubsub()
loop.add_future(future, stop_loop)
loop.start()
