#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tornado.testing
import tornado.ioloop

from tornadis.client import Client
from tornadis.exceptions import ClientError
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
