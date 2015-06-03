#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tornado.testing
import tornado.ioloop
import toro
import errno
import socket
from tornadis.connection import Connection
from tornadis.utils import format_args_in_redis_protocol
from support import test_redis_or_raise_skiptest
import hiredis
import functools
import random
import six


BIG_VALUE = six.b("".join(["%i" % random.randint(0, 9)
                           for x in range(0, 1000000)]))


class FakeSocketObject(object):

    def __init__(self, *args, **kwargs):
        cls = socket._socket.socket
        self.__socket = cls(*args, **kwargs)

    def setblocking(self, *args, **kwargs):
        return self.__socket.setblocking(*args, **kwargs)

    def connect(self, *args, **kwargs):
        return self.__socket.connect(*args, **kwargs)

    def fileno(self, *args, **kwargs):
        return self.__socket.fileno(*args, **kwargs)

    def close(self, *args, **kwargs):
        return self.__socket.close(*args, **kwargs)

    def getsockopt(self, *args, **kwargs):
        return self.__socket.getsockopt(*args, **kwargs)

    def setsockopt(self, *args, **kwargs):
        return self.__socket.setsockopt(*args, **kwargs)

    def recv(self, *args, **kwargs):
        return self.__socket.recv(*args, **kwargs)

    def send(self, *args, **kwargs):
        return self.__socket.send(*args, **kwargs)


class FakeSocketObject1(FakeSocketObject):

    def connect(self, *args, **kwargs):
        raise socket.error(errno.EWOULDBLOCK, "would block")


class FakeSocketObject2(FakeSocketObject):

    def __init__(self, *args, **kwargs):
        self.__first = True
        FakeSocketObject.__init__(self, *args, **kwargs)

    def send(self, *args, **kwargs):
        if self.__first:
            self.__first = False
            raise socket.error(errno.EWOULDBLOCK, "would block")
        else:
            return FakeSocketObject.send(self, *args, **kwargs)


class FakeSocketObject3(FakeSocketObject):

    def send(self, data):
        x = len(data)
        if x > 2:
            x = x / 2
        return FakeSocketObject.send(self, data[:x])


class FakeSocketObject4(FakeSocketObject):

    def __init__(self, *args, **kwargs):
        self.__first = True
        FakeSocketObject.__init__(self, *args, **kwargs)

    def recv(self, *args, **kwargs):
        if self.__first:
            self.__first = False
            raise socket.error(errno.EWOULDBLOCK, "would block")
        else:
            return FakeSocketObject.recv(self, *args, **kwargs)


def fake_socket_constructor(cls, *args, **kwargs):
    return cls(*args, **kwargs)


class ConnectionTestCase(tornado.testing.AsyncTestCase):

    def setUp(self):
        test_redis_or_raise_skiptest()
        super(ConnectionTestCase, self).setUp()
        self.reader = hiredis.Reader()
        self.reply_queue = toro.Queue()
        self.replies = []

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.instance()

    @tornado.testing.gen_test
    def test_init(self):
        c = Connection(self._read_cb, self._close_cb)
        yield c.connect()
        c.disconnect()

    def _close_cb(self):
        pass

    def _read_cb(self, data):
        self.reader.feed(data)
        while True:
            reply = self.reader.gets()
            if reply is not False:
                self.reply_queue.put_nowait(reply)
            else:
                break

    @tornado.testing.gen_test
    def test_init_with_tcp_nodelay(self):
        c = Connection(self._read_cb, self._close_cb, tcp_nodelay=True)
        yield c.connect()
        c.disconnect()

    @tornado.testing.gen_test
    def test_write(self):
        yield self._test_basic_write()

    @tornado.testing.gen_test
    def test_bigwrite(self):
        c = Connection(self._read_cb, self._close_cb)
        yield c.connect()
        data1 = format_args_in_redis_protocol("SET", "___foobar", BIG_VALUE)
        c.write(data1)
        data2 = format_args_in_redis_protocol("GET", "___foobar")
        c.write(data2)
        reply1 = yield self.reply_queue.get()
        reply2 = yield self.reply_queue.get()
        self.assertEquals(reply1, b"OK")
        self.assertEquals(reply2, BIG_VALUE)
        c.disconnect()

    @tornado.testing.gen_test
    def test_bad_connect(self):
        c = Connection(self._read_cb, self._close_cb, host="bad_host__")
        res = yield c.connect()
        self.assertFalse(res)
        c.disconnect()

    @tornado.testing.gen_test
    def test_timeout_connect(self):
        orig_constructor = socket.socket
        socket.socket = functools.partial(fake_socket_constructor,
                                          FakeSocketObject1)
        c = Connection(self._read_cb, self._close_cb, connect_timeout=2)
        res = yield c.connect()
        self.assertFalse(res)
        socket.socket = orig_constructor

    @tornado.gen.coroutine
    def _test_basic_write(self):
        c = Connection(self._read_cb, self._close_cb, connect_timeout=2)
        yield c.connect()
        data1 = format_args_in_redis_protocol("PING")
        data2 = b"*1\r\b$4\r\nQUIT\r\n"
        c.write(data1)
        c.write(data2)
        reply1 = yield self.reply_queue.get()
        self.assertEquals(reply1, b"PONG")
        reply2 = yield self.reply_queue.get()
        self.assertEquals(reply2, b"OK")
        c.disconnect()

    @tornado.testing.gen_test
    def test_blocking_write(self):
        orig_constructor = socket.socket
        socket.socket = functools.partial(fake_socket_constructor,
                                          FakeSocketObject2)
        yield self._test_basic_write()
        socket.socket = orig_constructor

    @tornado.testing.gen_test
    def test_blocking_read(self):
        orig_constructor = socket.socket
        socket.socket = functools.partial(fake_socket_constructor,
                                          FakeSocketObject4)
        yield self._test_basic_write()
        socket.socket = orig_constructor

    @tornado.testing.gen_test
    def test_partial_write(self):
        if six.PY3:
            self.skipTest("Breaks the test suite under Python 3")
        orig_constructor = socket.socket
        socket.socket = functools.partial(fake_socket_constructor,
                                          FakeSocketObject3)
        yield self._test_basic_write()
        socket.socket = orig_constructor

    @tornado.testing.gen_test
    def test_write_on_closed_socket(self):
        c = Connection(self._read_cb, self._close_cb, connect_timeout=2)
        yield c.connect()
        data1 = format_args_in_redis_protocol("PING")
        data2 = b"*1\r\b$4\r\nQUIT\r\n"
        c.write(data1)
        c.write(data2)
        reply1 = yield self.reply_queue.get()
        self.assertEquals(reply1, b"PONG")
        reply2 = yield self.reply_queue.get()
        self.assertEquals(reply2, b"OK")
        c.write(data1)
        # Wait a short moment while the server closes the socket
        yield tornado.gen.sleep(.0001)
        c._handle_write()
        c._handle_read()
        self.assertFalse(c.is_connected())
        c.disconnect()

    @tornado.testing.gen_test
    def test_already_connected(self):
        c = Connection(self._read_cb, self._close_cb, connect_timeout=2)
        res = yield c.connect()
        self.assertTrue(res)
        res = yield c.connect()
        self.assertTrue(res)
        c.disconnect()
