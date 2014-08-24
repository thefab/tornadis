#!/usr/bin/env python
# -*- coding: utf-8 -*-

import six
import tornado.testing

from tornadis.utils import format_args_in_redis_protocol


class UtilsTestCase(tornado.testing.AsyncTestCase):

    def test_protocol1(self):
        res = format_args_in_redis_protocol("PING")
        self.assertEquals(res, b"*1\r\n$4\r\nPING\r\n")

    def test_protocol2(self):
        res = format_args_in_redis_protocol("SET", "key", "foobar")
        self.assertEquals(res, b"*3\r\n$3\r\nSET\r\n$3\r\nkey\r\n"
                          b"$6\r\nfoobar\r\n")
        res = format_args_in_redis_protocol("SET", "key", six.u("foobar"))
        self.assertEquals(res, b"*3\r\n$3\r\nSET\r\n$3\r\nkey\r\n"
                          b"$6\r\nfoobar\r\n")

    def test_protocol3(self):
        res = format_args_in_redis_protocol("SET", "key", six.u("é"))
        self.assertEquals(res, b"*3\r\n$3\r\nSET\r\n$3\r\nkey\r\n"
                          b"$2\r\n\xc3\xa9\r\n")

    def test_protocol4(self):
        res = format_args_in_redis_protocol("SET", "key", b"\000")
        self.assertEquals(res, b"*3\r\n$3\r\nSET\r\n$3\r\nkey\r\n"
                          b"$1\r\n\000\r\n")

    def test_protocol5(self):
        res = format_args_in_redis_protocol("SET", "key", 1)
        self.assertEquals(res, b"*3\r\n$3\r\nSET\r\n$3\r\nkey\r\n"
                          b"$1\r\n1\r\n")
