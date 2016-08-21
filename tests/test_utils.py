#!/usr/bin/env python
# -*- coding: utf-8 -*-

import six
import tornado.testing
import tornado.concurrent

from tornadis.utils import format_args_in_redis_protocol
from tornadis.utils import ContextManagerFuture
from tornadis.write_buffer import WriteBuffer


class DummyException(Exception):
    pass


class UtilsTestCase(tornado.testing.AsyncTestCase):

    def test_protocol1(self):
        res = bytes(format_args_in_redis_protocol("PING"))
        self.assertEqual(res, b"*1\r\n$4\r\nPING\r\n")

    def test_protocol2(self):
        res = bytes(format_args_in_redis_protocol("SET", "key", "foobar"))
        self.assertEqual(res, b"*3\r\n$3\r\nSET\r\n$3\r\nkey\r\n"
                         b"$6\r\nfoobar\r\n")
        res = bytes(format_args_in_redis_protocol("SET", "key",
                                                  six.u("foobar")))
        self.assertEqual(res, b"*3\r\n$3\r\nSET\r\n$3\r\nkey\r\n"
                         b"$6\r\nfoobar\r\n")

    def test_protocol3(self):
        res = bytes(format_args_in_redis_protocol("SET", "key", six.u("\xe9")))
        self.assertEqual(res, b"*3\r\n$3\r\nSET\r\n$3\r\nkey\r\n"
                         b"$2\r\n\xc3\xa9\r\n")

    def test_protocol4(self):
        res = bytes(format_args_in_redis_protocol("SET", "key", b"\000"))
        self.assertEqual(res, b"*3\r\n$3\r\nSET\r\n$3\r\nkey\r\n"
                         b"$1\r\n\000\r\n")

    def test_protocol5(self):
        res = bytes(format_args_in_redis_protocol("SET", "key", 1))
        self.assertEqual(res, b"*3\r\n$3\r\nSET\r\n$3\r\nkey\r\n"
                         b"$1\r\n1\r\n")

    def test_protocol6(self):
        wb = WriteBuffer()
        wb.append(b"foobar")
        res = bytes(format_args_in_redis_protocol("SET", "key", wb))
        self.assertEqual(res, b"*3\r\n$3\r\nSET\r\n$3\r\nkey\r\n"
                         b"$6\r\nfoobar\r\n")

    def test_protocol_exception(self):
        self.assertRaises(Exception, format_args_in_redis_protocol, ["foo"])

    def _test_context_manager_future_cb(self):
        self._test_context_manager_future_cb_called = True

    @tornado.testing.gen_test
    def test_context_manager_future(self):
        self._test_context_manager_future_cb_called = False
        future = tornado.concurrent.Future()
        future.set_result("foobar")
        cb = self._test_context_manager_future_cb
        cmf = ContextManagerFuture(future, cb)
        with (yield cmf) as value:
            self.assertEqual(value, "foobar")
        boolean = self._test_context_manager_future_cb_called
        self.assertTrue(boolean)

    def _test_context_manager_future_exception_cb(self):
        self._test_context_manager_future_exception_cb_called = True

    @tornado.testing.gen_test
    def test_context_manager_future_exception(self):
        self._test_context_manager_future_exception_cb_called = False
        future = tornado.concurrent.Future()
        future.set_exception(DummyException())
        cb = self._test_context_manager_future_exception_cb
        cmf = ContextManagerFuture(future, cb)
        try:
            with (yield cmf):
                raise Exception("exception not raised")
            raise Exception("exception not raised")
        except DummyException:
            pass
        boolean = self._test_context_manager_future_exception_cb_called
        self.assertFalse(boolean)
