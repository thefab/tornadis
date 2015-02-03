import tornado
import tornadis
import datetime


@tornado.gen.coroutine
def ping_redis(pool):
    with (yield pool.connected_client()) as client:
        reply = yield client.call("PING")
        if reply != 'PONG':
            raise Exception('bad reply')


@tornado.gen.coroutine
def multiple_ping_redis(pool):
    clients = []
    for i in range(0, 100):
        client = yield pool.get_connected_client()
        clients.append(client)
    for i in range(0, 100):
        pool.release_client(clients[i])
    before = datetime.datetime.now()
    yield [ping_redis(pool) for i in range(0, 10000)]
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
