# Let's import tornado and tornadis
import tornado
import tornadis


@tornado.gen.coroutine
def pipeline_coroutine():
    # Let's make a pipeline object to stack commands inside
    pipeline = tornadis.Pipeline()
    pipeline.stack_call("SET", "foo", "bar")
    pipeline.stack_call("GET", "foo")

    # At this point, nothing is sent to redis

    # let's (re)connect (autoconnect mode), send the pipeline of requests
    # (atomic mode) and wait all replies without blocking the tornado ioloop.
    results = yield client.call(pipeline)

    if isinstance(results, tornadis.TornadisException):
        # For specific reasons, tornadis nearly never raises any exception
        # they are returned as result
        print "got exception: %s" % result
    else:
        # The two replies are in the results array
        print results
        # >>> ['OK', 'bar']


# Build a tornadis.Client object with some options as kwargs
# host: redis host to connect
# port: redis port to connect
# autoconnect=True: put the Client object in auto(re)connect mode
client = tornadis.Client(host="localhost", port=6379, autoconnect=True)

# Start a tornado IOLoop, execute the coroutine and end the program
loop = tornado.ioloop.IOLoop.instance()
loop.run_sync(pipeline_coroutine)
