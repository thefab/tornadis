#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tornado.testing
import tornado.ioloop

from tornadis.client import Client
from tornadis.pipeline import Pipeline
from tornadis.exceptions import ClientError
from support import test_redis_or_raise_skiptest


class PipelineTestCase(tornado.testing.AsyncTestCase):

    def setUp(self):
        test_redis_or_raise_skiptest()
        super(PipelineTestCase, self).setUp()

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.instance()

    @tornado.testing.gen_test
    def test_basic_pipeline(self):
        c = Client()
        yield c.connect()
        p = Pipeline()
        p.stack_call('PING')
        p.stack_call('PING')
        res = yield c.call(p)
        self.assertEqual(len(res), 2)
        self.assertEqual(res[0], b'PONG')
        self.assertEqual(res[1], b'PONG')
        c.disconnect()

    @tornado.testing.gen_test
    def test_empty_pipeline(self):
        c = Client()
        yield c.connect()
        p = Pipeline()
        res = yield c.call(p)
        self.assertTrue(isinstance(res, ClientError))
        c.disconnect()
