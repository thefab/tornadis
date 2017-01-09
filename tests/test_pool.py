#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tornado.testing
import tornado.ioloop
import time
import functools

from tornadis.pool import ClientPool
from tornadis.client import Client
from tornadis.exceptions import ClientError
from support import mock, test_redis_or_raise_skiptest


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
    def test_get_client_client_error(self):
        wrong_port = 11111

        c = ClientPool(max_size=1, port=wrong_port)

        client = yield c.get_connected_client()

        self.assertTrue(isinstance(client, ClientError))

        c.release_client(client)

        new_client = yield c.get_connected_client()

        self.assertTrue(isinstance(new_client, ClientError))

        c.destroy()

    @tornado.testing.gen_test
    def test_get_client_nowait1(self):
        c = ClientPool()
        client = c.get_client_nowait()
        self.assertTrue(isinstance(client, Client))
        c.release_client(client)
        c.destroy()

    @tornado.testing.gen_test
    def test_get_client_nowait2(self):
        c = ClientPool(max_size=1)
        client1 = c.get_client_nowait()
        self.assertTrue(isinstance(client1, Client))
        client2 = c.get_client_nowait()
        self.assertTrue(client2 is None)
        c.release_client(client1)
        c.destroy()

    @tornado.testing.gen_test
    def test_get_client_context_manager(self):
        c = ClientPool(max_size=1)
        with (yield c.connected_client()) as client:
            pass
        client = yield c.get_connected_client()
        c.release_client(client)
        c.destroy()

    @tornado.testing.gen_test
    def test_get_client_select_db_after_connect(self):
        db = 13
        c = ClientPool(db=db)
        client = yield c.get_connected_client()
        self.assertIsInstance(client, Client)
        self.assertEqual(db, client.db)
        c.release_client(client)
        c.destroy()

    @tornado.testing.gen_test
    def test_get_client_invalid_select_db_after_connect(self):
        db = 'non-existent-db'
        c = ClientPool(db=db)
        client = yield c.get_connected_client()
        self.assertIsInstance(client, ClientError)
        c.destroy()

    @tornado.testing.gen_test
    def test_preconnect1(self):
        c = ClientPool(max_size=-1)
        try:
            yield c.preconnect()
            raise Exception("ClientError not raised")
        except ClientError:
            pass

    @tornado.testing.gen_test
    def test_preconnect2(self):
        c = ClientPool(max_size=5)
        yield c.preconnect(5)
        pool = c._ClientPool__pool
        for i in range(0, 5):
            client = pool.popleft()
            self.assertTrue(client.is_connected())
        for i in range(0, 5):
            pool.append(client)
        c.destroy()

    @tornado.testing.gen_test
    def test_timeout(self):
        c = ClientPool(max_size=5, client_timeout=1)
        client1 = yield c.get_connected_client()
        c.release_client(client1)
        client2 = yield c.get_connected_client()
        c.release_client(client2)
        self.assertTrue(client1 == client2)
        yield tornado.gen.sleep(1)
        client3 = yield c.get_connected_client()
        self.assertFalse(client1 == client3)
        c.release_client(client3)
        c.destroy()

    @tornado.testing.gen_test
    def test_constructor(self):
        c = ClientPool(max_size=-1, client_timeout=-1, port=6379,
                       host="localhost", password="foo")
        with (yield c.connected_client()) as client:
            self.assertTrue(isinstance(client, ClientError))
            pass
        c.destroy()

    @tornado.testing.gen_test
    def test_autoclose(self):
        c = ClientPool(max_size=5, client_timeout=1, autoclose=True)
        client1 = yield c.get_connected_client()
        self.assertTrue(client1.is_connected())
        c.release_client(client1)
        yield tornado.gen.sleep(3)
        self.assertFalse(client1.is_connected())
        c.destroy()

    @tornado.testing.gen_test
    def test_release_expired_client_disconnect(self):
        with mock.patch.object(ClientPool,
                               '_is_expired_client',
                               return_value=True):
            c = ClientPool(max_size=5, client_timeout=60, autoclose=False)
            client = yield c.get_connected_client()
            self.assertTrue(client.is_connected())
            c.release_client(client)
            self.assertFalse(client.is_connected())
