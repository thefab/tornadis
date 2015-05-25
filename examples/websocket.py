import tornado
from tornado.websocket import WebSocketHandler
from tornado.web import RequestHandler, Application, url
import tornadis


clients = []


class GetHandler(RequestHandler):

    @tornado.gen.coroutine
    def get(self):
        self.render("websocket.html")


class WSHandler(WebSocketHandler):

    @tornado.gen.coroutine
    def initialize(self):
        self.redis = tornadis.Client()
        loop = tornado.ioloop.IOLoop.current()
        loop.add_callback(self.watch_redis)

    @tornado.gen.coroutine
    def watch_redis(self):
        while True:
            response = yield self.redis.call('BLPOP', 'ws-queue', 0)
            for client in clients:
                client.write_message(response[1])

    def open(self, *args):
        clients.append(self)

    @tornado.gen.coroutine
    def on_message(self, message):
        yield self.redis.call('LPUSH', 'ws-queue', message)

    def on_close(self):
        clients.remove(self)


app = Application([
    url(r"/", GetHandler),
    url(r"/ws", WSHandler)
])

if __name__ == '__main__':
    app.listen(8888)
    tornado.ioloop.IOLoop.current().start()
