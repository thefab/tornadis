Introduction
------------

Let's see how to get started with tornadis using the `Client` class: In
the following example, we connect to Redis and terminate the program
when we're connected or if an error occurs::


    # tornadis/examples/connection.py
    import tornado
    import tornadis

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

While this example in itself is not very useful, it demonstrates the
asynchronous nature of Tornadis. The statement ``client.connect()``
doesn't block but returns a tornado Future. When adding
the future to the I/O event loop, we also specify a callback function which
wil be called once the future has done its job. In the callback, we
check if the execution of the future has raised any exception.

Now that we know how to connect to Redis, let's try to send a ``PING``
command::

    # tornadis/examples/callbacks.py
    # imports omitted for brievety

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


In the callback that gets executed once we're connected to Redis, we
call the client's ``call`` method, which also returns a Tornado future.
We add that future to the I/O loop, also specifying a callback to
execute once the command has completed. If we need to send a longer
sequence of commands to Redis, you can see how this style of
asynchronous programming can quickly lead to a tangled chain of callback
functions.

Fortunately, Tornado and therefore Tornadis allow a different style of asynchronous code using
coroutines based on Python generators. Let's refactor the previous code
snippet to use a coroutine::

    # tornadis/examples/coroutines.py
    loop = tornado.ioloop.IOLoop.instance()
    client = tornadis.Client()


    def callback(future):
        exception = future.exception()
        if exception is not None:
            raise exception
        loop.stop()


    @tornado.gen.coroutine
    def talk_to_redis():
        yield client.connect()
        result = yield client.call("PING")
        print "Result: %s" % result


    connect_future = client.connect()
    main_future = talk_to_redis()
    loop.add_future(main_future, callback)
    loop.start()


When we call our coroutine, it returns a future. We add that main future
as before to the I/O loop. But whereas in the previous example, we had
to explicitely add our second asynchronous command to the I/O loop along
with its own callback, using a coroutine allows us to send our command
as a single statement and retrieve its result with a regular variable
assignment. We just need to remember to add the ``yield`` keyword before
the asynchronous command invocation.

In the context of an HTTP request handler, we don't need to add our
top-level coroutine to the I/O loop ourselves, because the framework
handles it for us::

    import tornado
    from tornado.web import RequestHandler, Application, url
    import tornadis


    class GetHandler(RequestHandler):

        @tornado.gen.coroutine
        def get(self):
            client = tornadis.Client(port=6379)
            yield client.connect()
            yield client.call("BLPOP", "empty", 3)
            self.finish()


    app = Application([url(r"/", GetHandler)])
    app.listen(8888)
    tornado.ioloop.IOLoop.current().start()
