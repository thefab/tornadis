#!/usr/bin/env python
# -*- coding: utf-8 -*-

import socket
import unittest


try:
    from unittest import mock  # noqa
except ImportError:
    try:
        import mock  # noqa
    except ImportError:
        pass


def test_redis_or_raise_skiptest(host="localhost", port=6379):
    s = socket.socket()
    try:
        s.connect((host, port))
    except socket.error:
        raise unittest.SkipTest("redis must be launched on %s:%i" % (host,
                                                                     port))
    finally:
        s.close()


def test_redis_uds_or_raise_skiptest(uds="/tmp/redis.sock"):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        s.connect(uds)
    except socket.error:
        raise unittest.SkipTest("redis must listen on %s" % uds)
    finally:
        s.close()


def fake_socket_constructor(cls, *args, **kwargs):
    return cls(*args, **kwargs)


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
