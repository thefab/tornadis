#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of tornadis library released under the MIT license.
# See the LICENSE file for more information.

import socket
import tornado.iostream
import tornado.gen

# FIXME: error handling


class Connection(object):

    def __init__(self, host='localhost', port=6379, ioloop=None):
        self.host = host
        self.port = port
        self.connected = False
        self.__stream = None
        self.__ioloop = ioloop or tornado.ioloop.IOLoop.instance()

    @tornado.gen.coroutine
    def connect(self):
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__stream = tornado.iostream.IOStream(self.__socket,
                                                  io_loop=self.__ioloop)
        yield self.__stream.connect((self.host, self.port))
        self.connected = True

    def disconnect(self):
        self.__stream.close()
        self.connected = False

    def write(self, data):
        return self.__stream.write(data)

    def register_read_until_close_callback(self, callback=None,
                                           streaming_callback=None):
        self.__stream.read_until_close(callback=callback,
                                       streaming_callback=streaming_callback)
