import tornado
import tornadis


@tornado.gen.coroutine
def pubsub_coroutine():
    # Let's get a connected client
    # we don't use autoconnect=True because issue #22
    client = tornadis.PubSubClient(autoconnect=False)
    yield client.connect()

    # Let's "psubscribe" to a pattern
    yield client.pubsub_psubscribe("foo*")

    # Let's "subscribe" to a channel
    yield client.pubsub_subscribe("bar")

    # Looping over received messages
    while True:
        # Let's "block" until a message is available
        msg = yield client.pubsub_pop_message()
        print(msg)
        # >>> ['pmessage', 'foo*', 'foo', 'bar']
        # (for a "publish foo bar" command from another connection)

        if isinstance(msg, tornadis.TornadisException):
            # closed connection by the server
            break
        elif len(msg) >= 4 and msg[3] == "STOP":
            # it's a STOP message, let's unsubscribe and quit the loop
            yield client.pubsub_punsubscribe("foo*")
            yield client.pubsub_unsubscribe("bar")
            break

    # Let's disconnect
    client.disconnect()


loop = tornado.ioloop.IOLoop.instance()
loop.run_sync(pubsub_coroutine)
