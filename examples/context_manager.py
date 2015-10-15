import tornado
import tornadis


@tornado.gen.coroutine
def ping_redis(num):
    with (yield pool.connected_client()) as client:
        if not isinstance(client, tornadis.TornadisException):
            # client is a connected tornadis.Client instance
            # it will be automatically released to the pool thanks to the
            # "with" keyword
            reply = yield client.call("PING")
            if not isinstance(reply, tornadis.TornadisException):
                print("reply #%i : %s" % (num, reply))


@tornado.gen.coroutine
def multiple_ping_redis():
    yield [ping_redis(i) for i in range(0, 100)]


pool = tornadis.ClientPool(max_size=5)
loop = tornado.ioloop.IOLoop.instance()
loop.run_sync(multiple_ping_redis)
pool.destroy()
