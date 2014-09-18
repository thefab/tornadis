#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of tornadis library released under the MIT license.
# See the LICENSE file for more information.

import socket
import tornado.iostream
import tornado.gen
from tornadis.exceptions import ConnectionError


class Connection(object):
    """Low level connection object.

    Attributes:
        host (string): the host name to connect to.
        port (int): the port to connect to.
        connected (boolean): is the connection object really connected.
    """

    def __init__(self, host='localhost', port=6379, ioloop=None):
        """Constructor.

        Args:
            host (string): the host name to connect to.
            port (int): the port to connect to.
            ioloop (IOLoop): the tornado ioloop to use.
        """
        self.host = host
        self.port = port
        self.connected = False
        self.__stream = None
        self.__ioloop = ioloop or tornado.ioloop.IOLoop.instance()

    @tornado.gen.coroutine
    def connect(self):
        """Connects the object to the host:port.

        Returns:
            Future: a Future object with no specific result.
        """
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__stream = tornado.iostream.IOStream(self.__socket,
                                                  io_loop=self.__ioloop)
        future = self.__stream.connect((self.host, self.port))
        if future is None:
            raise ConnectionError("can't connect to %s:%i" % (self.host,
                                                              self.port))
        try:
            yield future
        except:
            raise ConnectionError("can't connect to %s:%i" % (self.host,
                                                              self.port))
        self.connected = True

    def disconnect(self):
        """Disconnects the object.
        """
        self.__stream.close()
        self.connected = False

    def write(self, data):
        """Writes some data to the host:port

        Args:
            data (str): string (buffer) to write to the host:port

        Returns:
            Future: a Future object "resolved" when the data is written
                on the socket (no specific result)
        """
        return self.__stream.write(data)

    def register_read_until_close_callback(self, callback=None,
                                           streaming_callback=None):
        """Registers a callback called when data are available on the socket.

        The callback is called with the data as argument.

        Args:
            callback (callable): callback to call when the connection is
                closed
            streaming_callback (callable): callback to call when data are
                available on the socket
        """
        self.__stream.read_until_close(callback=callback,
                                       streaming_callback=streaming_callback)
