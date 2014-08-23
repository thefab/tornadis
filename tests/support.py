#!/usr/bin/env python
# -*- coding: utf-8 -*-

import socket
import unittest


def test_redis_or_raise_skiptest(host="localhost", port=6379):
    s = socket.socket()
    try:
        s.connect((host, port))
    except socket.error:
        raise unittest.SkipTest("redis must be launched on %s:%i" % (host,
                                                                     port))
