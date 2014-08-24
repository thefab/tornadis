#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tornado.testing
import tornado.ioloop
import toro

from tornadis.connection import Connection
from tornadis.utils import format_args_in_redis_protocol
from support import test_redis_or_raise_skiptest


class ConnectionTestCase(tornado.testing.AsyncTestCase):

    def setUp(self):
        test_redis_or_raise_skiptest()
        super(ConnectionTestCase, self).setUp()

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.instance()

    @tornado.testing.gen_test
    def test_init(self):
        c = Connection()
        yield c.connect()
        c.disconnect()

    def _test_write_cb(self, data):
        self.assertEquals(data, b"+PONG\r\n+OK\r\n")
        self._test_write_condition.notify()

    @tornado.testing.gen_test
    def test_write(self):
        self._test_write_condition = toro.Condition()
        c = Connection()
        yield c.connect()
        data1 = format_args_in_redis_protocol("PING")
        data2 = format_args_in_redis_protocol("QUIT")
        cb = self._test_write_cb
        c.register_read_until_close_callback(callback=cb)
        yield c.write(data1)
        yield c.write(data2)
        yield self._test_write_condition.wait()
        c.disconnect()
