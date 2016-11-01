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
