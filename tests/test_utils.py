#!/usr/bin/env python
# -*- coding: utf-8 -*-

import six
import tornado.testing
import tornado.concurrent

from tornadis.utils import format_args_in_redis_protocol
from tornadis.utils import ContextManagerFuture
from tornadis.utils import WriteBuffer


class DummyException(Exception):
    pass


class UtilsTestCase(tornado.testing.AsyncTestCase):

    def test_protocol1(self):
        res = bytes(format_args_in_redis_protocol("PING"))
        self.assertEquals(res, b"*1\r\n$4\r\nPING\r\n")

    def test_protocol2(self):
        res = bytes(format_args_in_redis_protocol("SET", "key", "foobar"))
        self.assertEquals(res, b"*3\r\n$3\r\nSET\r\n$3\r\nkey\r\n"
                          b"$6\r\nfoobar\r\n")
        res = bytes(format_args_in_redis_protocol("SET", "key",
                                                  six.u("foobar")))
        self.assertEquals(res, b"*3\r\n$3\r\nSET\r\n$3\r\nkey\r\n"
                          b"$6\r\nfoobar\r\n")

    def test_protocol3(self):
        res = bytes(format_args_in_redis_protocol("SET", "key", six.u("\xe9")))
        self.assertEquals(res, b"*3\r\n$3\r\nSET\r\n$3\r\nkey\r\n"
                          b"$2\r\n\xc3\xa9\r\n")

    def test_protocol4(self):
        res = bytes(format_args_in_redis_protocol("SET", "key", b"\000"))
        self.assertEquals(res, b"*3\r\n$3\r\nSET\r\n$3\r\nkey\r\n"
                          b"$1\r\n\000\r\n")

    def test_protocol5(self):
        res = bytes(format_args_in_redis_protocol("SET", "key", 1))
        self.assertEquals(res, b"*3\r\n$3\r\nSET\r\n$3\r\nkey\r\n"
                          b"$1\r\n1\r\n")

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
            self.assertEquals(value, "foobar")
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

    def _make_test_buffer(self):
        x = WriteBuffer()
        x.append(b"23")
        x.append(b"4")
        x.append(b"")
        x.append(b"56789")
        x.appendleft(b"1")
        return x

    def _get_chunk_as_str(self, buf, max_size):
        tmp = buf.get_chunk(max_size)
        if isinstance(tmp, memoryview):
            return tmp.tobytes()
        else:
            return tmp

    def test_write_buffer1(self):
        b = self._make_test_buffer()
        s = bytes(b)
        self.assertEquals(s, b"123456789")
        self.assertFalse(b.is_empty())
        self.assertEquals(b._total_length, 9)
        b2 = self._make_test_buffer()
        b.extend(b2)
        s = bytes(b)
        self.assertEquals(s, b"123456789123456789")
        self.assertFalse(b.is_empty())
        self.assertEquals(b._total_length, 18)
        chunk = self._get_chunk_as_str(b, 1000)
        self.assertEquals(chunk, b"123456789123456789")
        self.assertTrue(b.is_empty())

    def test_write_buffer2(self):
        b = self._make_test_buffer()
        chunk = self._get_chunk_as_str(b, 1)
        self.assertEquals(chunk, b"1")
        self.assertEquals(bytes(b), b"23456789")
        self.assertEquals(b._total_length, 8)
        chunk = self._get_chunk_as_str(b, 1)
        self.assertEquals(chunk, b"2")
        self.assertEquals(bytes(b), b"3456789")
        self.assertEquals(b._total_length, 7)
        chunk = self._get_chunk_as_str(b, 4)
        self.assertEquals(chunk, b"3456")
        self.assertEquals(bytes(b), b"789")
        self.assertEquals(b._total_length, 3)
        chunk = self._get_chunk_as_str(b, 10)
        self.assertEquals(chunk, b"789")
        self.assertEquals(bytes(b), b"")
        self.assertEquals(b._total_length, 0)

    def test_write_buffer3(self):
        b = WriteBuffer()
        b.append(b"x" * 10000)
        chunk = self._get_chunk_as_str(b, 4000)
        self.assertEquals(len(chunk), 4000)
        chunk = self._get_chunk_as_str(b, 4000)
        self.assertEquals(len(chunk), 4000)
        chunk = self._get_chunk_as_str(b, 4000)
        self.assertEquals(len(chunk), 2000)
