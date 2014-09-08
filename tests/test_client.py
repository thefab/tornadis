#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tornado.testing
import tornado.ioloop

from tornadis.client import Client
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
    def test_pubsub(self):
        c = Client()
        c2 = Client()
        yield c.connect()
        yield c2.connect()
        try:
            yield c.pubsub_pop_message()
            raise Exception("exception not raised")
        except:
            pass
        res = yield c.pubsub_subscribe("foo1", "foo2")
        self.assertTrue(res)
        self.assertTrue(c.subscribed)
        self.assertFalse(c2.subscribed)
        try:
            yield c.call("PING")
            raise Exception("exception not raised")
        except:
            pass
        res = yield c.pubsub_psubscribe("bar1*", "bar2*")
        self.assertTrue(res)
        yield c2.call("PUBLISH", "null", "value0")
        yield c2.call("PUBLISH", "foo1", "value1")
        yield c2.call("PUBLISH", "foo2", "value2")
        yield c2.call("PUBLISH", "bar111", "value3")
        yield c2.call("PUBLISH", "bar222", "value4")
        msg = yield c.pubsub_pop_message()
        self.assertEquals(msg[2], "value1")
        msg = yield c.pubsub_pop_message()
        self.assertEquals(msg[2], "value2")
        msg = yield c.pubsub_pop_message()
        self.assertEquals(msg[3], "value3")
        msg = yield c.pubsub_pop_message()
        self.assertEquals(msg[3], "value4")
        msg = yield c.pubsub_pop_message(deadline=1)
        self.assertEquals(msg, None)
        yield c.pubsub_unsubscribe("foo1")
        yield c2.call("PUBLISH", "foo1", "value1")
        yield c2.disconnect()
        msg = yield c.pubsub_pop_message(deadline=1)
        self.assertEquals(msg, None)
        yield c.pubsub_unsubscribe("foo2")
        yield c.pubsub_unsubscribe("foobar")
        yield c.pubsub_punsubscribe("foobar*")
        yield c.pubsub_punsubscribe("bar1*")
        yield c.pubsub_punsubscribe("bar2*")
        self.assertFalse(c.subscribed)
        res = yield c.call("PING")
        self.assertEquals(res, "PONG")
        yield c.disconnect()
