#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of tornadis library released under the MIT license.
# See the LICENSE file for more information.

import tornado.ioloop
import tornado.gen
import hiredis
import toro

from tornadis.connection import Connection
from tornadis.pipeline import Pipeline
from tornadis.utils import format_args_in_redis_protocol

# FIXME: error handling


class Client(object):

    def __init__(self, host='localhost', port=6379, ioloop=None):
        self.host = host
        self.port = port
        self.__reply_queue = toro.Queue()
        self.__ioloop = ioloop or tornado.ioloop.IOLoop.instance()
        self.reader = hiredis.Reader()
        self.__connection = Connection(host=host, port=port,
                                       ioloop=self.__ioloop)

    @tornado.gen.coroutine
    def connect(self):
        yield self.__connection.connect()
        cb1 = self._close_callback
        cb2 = self._read_callback
        self.__connection.register_read_until_close_callback(cb1, cb2)

    def disconnect(self):
        return self.call("QUIT")

    def _disconnect(self):
        self.__connection.disconnect()

    def _close_callback(self, data=None):
        if data is not None:
            self._read_callback(data)
        self._disconnect()

    def _read_callback(self, data=None):
        if data is not None:
            self.reader.feed(data)
            while True:
                reply = self.reader.gets()
                if reply is not False:
                    self.__reply_queue.put_nowait(reply)
                else:
                    break

    def call(self, *args):
        if len(args) == 1 and isinstance(args[0], Pipeline):
            return self._pipelined_call(args[0])
        else:
            return self._simple_call(*args)

    @tornado.gen.coroutine
    def _simple_call(self, *args):
        msg = format_args_in_redis_protocol(*args)
        yield self.__connection.write(msg)
        reply = yield self.__reply_queue.get()
        raise tornado.gen.Return(reply)

    @tornado.gen.coroutine
    def _pipelined_call(self, pipeline):
        for args in pipeline.args_generator():
            msg = format_args_in_redis_protocol(*args)
            yield self.__connection.write(msg)
        result = []
        i = 0
        while i < pipeline.number_of_stacked_calls:
            reply = yield self.__reply_queue.get()
            result.append(reply)
            i = i + 1
        raise tornado.gen.Return(result)
