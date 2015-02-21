import tornado
import tornadis


@tornado.gen.coroutine
def pipeline_coroutine():
    # Let's get a connected client
    client = tornadis.Client()
    yield client.connect()

    # Let's make a pipeline object to stack commands inside
    pipeline = tornadis.Pipeline()
    pipeline.stack_call("SET", "foo", "bar")
    pipeline.stack_call("GET", "foo")

    # At this point, nothing is sent to redis

    # Let's submit the pipeline to redis and wait for replies
    results = yield client.call(pipeline)

    # The two replies are in the results array
    print results
    # >>> ['OK', 'bar']

    # Let's disconnect
    client.disconnect()


def stop_loop(future):
    exception = future.exception()
    if exception is not None:
        raise(exception)
    loop.stop()


loop = tornado.ioloop.IOLoop.instance()
loop.add_future(pipeline_coroutine(), stop_loop)
loop.start()
