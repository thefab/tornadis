#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tornado.testing
import tornado.ioloop
import time
import functools

from tornadis.pool import ClientPool
from tornadis.client import Client
from support import test_redis_or_raise_skiptest


class ClientPoolTestCase(tornado.testing.AsyncTestCase):

    def setUp(self):
        test_redis_or_raise_skiptest()
        super(ClientPoolTestCase, self).setUp()

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.instance()

    @tornado.testing.gen_test
    def test_init(self):
        c = ClientPool()
        c.destroy()

    @tornado.testing.gen_test
    def test_get_client1(self):
        c = ClientPool()
        client = yield c.get_connected_client()
        self.assertTrue(isinstance(client, Client))
        c.release_client(client)
        c.destroy()

    def _test_get_client2_cb(self, pool, client):
        pool.release_client(client)
        self._test_get_client2_cb_called = True

    @tornado.testing.gen_test
    def test_get_client2(self):
        c = ClientPool(max_size=2)
        client1 = yield c.get_connected_client()
        self.assertTrue(isinstance(client1, Client))
        client2 = yield c.get_connected_client()
        self.assertTrue(isinstance(client2, Client))
        ioloop = tornado.ioloop.IOLoop.instance()
        deadline = time.time() + 1
        cb = functools.partial(self._test_get_client2_cb, c, client1)
        self._test_get_client2_cb_called = False
        ioloop.add_timeout(deadline, cb)
        client3 = yield c.get_connected_client()
        self.assertTrue(self._test_get_client2_cb_called)
        self.assertTrue(client1 == client3)
        c.release_client(client2)
        c.release_client(client3)
        c.destroy()

    @tornado.testing.gen_test
    def test_get_client_context_manager(self):
        c = ClientPool(max_size=1)
        with (yield c.connected_client()) as client:
            pass
        client = yield c.get_connected_client()
        c.release_client(client)
        c.destroy()
