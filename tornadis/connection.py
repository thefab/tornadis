#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of tornadis library released under the MIT license.
# See the LICENSE file for more information.

import socket
import tornado.iostream
import tornado.gen
from tornadis.exceptions import ConnectionError
import tornadis


class Connection(object):
    """Low level connection object.

    Attributes:
        host (string): the host name to connect to.
        port (int): the port to connect to.
        connect_timeout (int): connect timeout (seconds)
        write_timeout (int): write timeout (seconds)
        connected (boolean): is the connection object really connected.
    """

    def __init__(self, host=tornadis.DEFAULT_HOST, port=tornadis.DEFAULT_PORT,
                 connect_timeout=tornadis.DEFAULT_CONNECT_TIMEOUT,
                 write_timeout=tornadis.DEFAULT_WRITE_TIMEOUT,
                 ioloop=None):
        """Constructor.

        Args:
            host (string): the host name to connect to.
            port (int): the port to connect to.
            connect_timeout (int): connection timeout (seconds)
            write_timeout (int): write timeout (seconds)
            ioloop (IOLoop): the tornado ioloop to use.
        """
        self.host = host
        self.port = port
        self.connect_timeout = connect_timeout
        self.write_timeout = write_timeout
        self.connected = False
        self.__stream = None
        self.__ioloop = ioloop or tornado.ioloop.IOLoop.instance()

    @tornado.gen.coroutine
    def connect(self):
        """Connects the object to the host:port.

        Returns:
            Future: a Future object with no specific result.

        Raises:
            ConnectionError: when there is a connection error
        """
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__stream = tornado.iostream.IOStream(self.__socket,
                                                  io_loop=self.__ioloop)
        cb = self._timeout_callback
        handle = self.__ioloop.call_later(self.connect_timeout, cb)
        try:
            yield self.__stream.connect((self.host, self.port))
        except:
            self.__ioloop.remove_timeout(handle)
            raise ConnectionError("can't connect to %s:%i" % (self.host,
                                                              self.port))
        self.__ioloop.remove_timeout(handle)
        self.connected = True

    def _timeout_callback(self):
        self.disconnect()

    def disconnect(self):
        """Disconnects the object.
        """
        self.__stream.close()
        self.connected = False

    @tornado.gen.coroutine
    def write(self, data):
        """Writes some data to the host:port

        Args:
            data (str): string (buffer) to write to the host:port

        Returns:
            Future: a Future object "resolved" when the data is written
                on the socket (no specific result)

        Raises:
            ConnectionError: when there is a connection error
        """
        if not self.connected:
            raise ConnectionError("you are not connected")
        cb = self._timeout_callback
        handle = self.__ioloop.call_later(self.write_timeout, cb)
        try:
            result = yield self.__stream.write(data)
        except:
            self.__ioloop.remove_timeout(handle)
            self.disconnect()
            raise ConnectionError("can't write to socket")
        self.__ioloop.remove_timeout(handle)
        raise tornado.gen.Return(result)

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
