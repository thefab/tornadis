#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tornado.testing
import tornado.ioloop
import tornado

from tornadis.client import Client
from tornadis.exceptions import ClientError, ConnectionError
from support import test_redis_or_raise_skiptest


class ClientTestCase(tornado.testing.AsyncTestCase):

    def setUp(self):
        test_redis_or_raise_skiptest()
        super(ClientTestCase, self).setUp()

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.instance()

    @tornado.testing.gen_test
    def test_init(self):
        c = Client()
        yield c.connect()
        yield c.disconnect()

    @tornado.testing.gen_test
    def test_ping(self):
        c = Client()
        yield c.connect()
        res = yield c.call('PING')
        self.assertEquals(res, b"PONG")
        yield c.disconnect()

    @tornado.testing.gen_test
    def test_discard(self):
        c = Client()
        yield c.connect()
        c.call('PING', discard_reply=True)
        yield c.disconnect()

    @tornado.testing.gen_test
    def test_discard_and_callback(self):
        c = Client()
        yield c.connect()
        try:
            c.call('PING', discard_reply=True, callback=lambda x: x)
            raise Exception("ClientError not raised")
        except ClientError:
            pass
        yield c.disconnect()

    @tornado.gen.coroutine
    def _close_connection(self, client):
        yield tornado.gen.sleep(1)
        yield client.call("CLIENT", "KILL", "SKIPME", "YES")

    @tornado.testing.gen_test
    def test_server_close_connection(self):
        c = Client(return_connection_error=True)
        c2 = Client()
        yield c.connect()
        yield c2.connect()
        future1 = c.call('BLPOP', 'test_server_close_connection', 0)
        future2 = self._close_connection(c2)
        res = yield [future1, future2]
        self.assertTrue(isinstance(res[0], ConnectionError))
        self.assertFalse(c.is_connected())
        yield c.connect()
        res2 = yield c.call("PING")
        self.assertEquals(res2, "PONG")
        yield c.disconnect()
        yield c2.disconnect()
