#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of tornadis library released under the MIT license.
# See the LICENSE file for more information.

import tornado.ioloop
import tornado.gen
import hiredis
import toro
import io

from tornadis.connection import Connection
from tornadis.pipeline import Pipeline
from tornadis.utils import format_args_in_redis_protocol, StopObject
from tornadis.exceptions import ConnectionError, ClientError
import tornadis

# FIXME: error handling


class Client(object):
    """High level object to interact with redis.

    Attributes:
        host (string): the host name to connect to.
        port (int): the port to connect to.
        connect_timeout (int): connect timeout (seconds)
        write_timeout (int): write timeout (seconds)
        read_timeout (int): read timeout (seconds) (not used with
            pubsub_pop_message() which has a specific deadline parameter)
        subscribed (boolean): is the client object subscribed to redis
            (with pubsub methods).
        __reply_queue (toro.Queue): toro queue to put redis replies.
        __reader: hiredis reader object.
        __connection: tornadis low level Connection object.
    """

    def __init__(self, host=tornadis.DEFAULT_HOST, port=tornadis.DEFAULT_PORT,
                 connect_timeout=tornadis.DEFAULT_CONNECT_TIMEOUT,
                 write_timeout=tornadis.DEFAULT_WRITE_TIMEOUT,
                 read_timeout=tornadis.DEFAULT_READ_TIMEOUT,
                 ioloop=None):
        """Constructor.

        Args:
            host (string): the host name to connect to.
            port (int): the port to connect to.
            connect_timeout (int): connect timeout (seconds)
            write_timeout (int): write timeout (seconds)
            read_timeout (int): read timeout (seconds)
            ioloop (IOLoop): the tornado ioloop to use.
        """
        self.host = host
        self.port = port
        self.connect_timeout = connect_timeout
        self.write_timeout = write_timeout
        self.read_timeout = read_timeout
        self.subscribed = False
        self.__ioloop = ioloop or tornado.ioloop.IOLoop.instance()
        self.__connection = None

    def is_connected(self):
        """Returns True is the client is connected to redis.

        Returns:
            True if the client if connected to redis.
        """
        return (self.__connection is not None) and \
               (self.__connection.connected)

    @tornado.gen.coroutine
    def connect(self):
        """Connects the client object to redis.

        Returns:
            a Future object with no result.
        """
        cb1 = self._close_callback
        cb2 = self._read_callback
        self.__reply_queue = toro.Queue()
        self.__reader = hiredis.Reader()
        self.__connection = Connection(host=self.host, port=self.port,
                                       connect_timeout=self.connect_timeout,
                                       write_timeout=self.write_timeout,
                                       ioloop=self.__ioloop)
        yield self.__connection.connect()
        self.__connection.register_read_until_close_callback(cb1, cb2)

    def disconnect(self):
        """Disconnects the client object from redis.

        Returns:
            a Future object with no result.
        """
        return self._simple_call("QUIT")

    def _close_callback(self, data=None):
        """Callback called when redis closed the connection.

        Args:
            data (str): string (buffer) read on the socket just before redis
                closed the connection.
        """
        if data is not None:
            self._read_callback(data)
        self.__reply_queue.put_nowait(StopObject())
        self.__connection.disconnect()

    def _read_callback(self, data=None):
        """Callback called when some data are read on the socket.

        The buffer is given to the hiredis parser. If a reply is complete,
        we put the decoded reply to on the reply queue.

        Args:
            data (str): string (buffer) read on the socket.
        """
        if data is not None:
            self.__reader.feed(data)
            while True:
                reply = self.__reader.gets()
                if reply is not False:
                    self.__reply_queue.put_nowait(reply)
                else:
                    break

    def call(self, *args):
        """Calls a redis command and waits for the reply

        Args:
            *args: full redis command as variable length argument list

        Returns:
            a Future with the decoded redis reply as result

        Examples:

            >>> @tornado.gen.coroutine
                def foobar():
                    client = Client()
                    result = yield client.call("HSET", "key", "field", "value")
        """
        if self.subscribed:
            raise ClientError("This client is in subscription mode, "
                              "only pubsub_* command are allowed")
        if len(args) == 1 and isinstance(args[0], Pipeline):
            return self._pipelined_call(args[0])
        else:
            return self._simple_call(*args)

    @tornado.gen.coroutine
    def _simple_call(self, *args):
        msg = format_args_in_redis_protocol(*args)
        yield self.__connection.write(msg)
        reply = yield self._reply_queue_get()
        raise tornado.gen.Return(reply)

    def _simple_call_without_pop_reply(self, *args):
        msg = format_args_in_redis_protocol(*args)
        return self.__connection.write(msg)

    def pubsub_subscribe(self, *args):
        return self._pubsub_subscribe(b"SUBSCRIBE", *args)

    def pubsub_psubscribe(self, *args):
        return self._pubsub_subscribe(b"PSUBSCRIBE", *args)

    @tornado.gen.coroutine
    def _pubsub_subscribe(self, command, *args):
        yield self._simple_call_without_pop_reply(command, *args)
        for _ in args:
            reply = yield self._reply_queue_get()
            if len(reply) != 3 or reply[0].lower() != command.lower() or \
               reply[2] == 0:
                raise tornado.gen.Return(False)
        self.subscribed = True
        raise tornado.gen.Return(True)

    def pubsub_unsubscribe(self, *args):
        return self._pubsub_unsubscribe(b"UNSUBSCRIBE", *args)

    def pubsub_punsubscribe(self, *args):
        return self._pubsub_unsubscribe(b"PUNSUBSCRIBE", *args)

    @tornado.gen.coroutine
    def _pubsub_unsubscribe(self, command, *args):
        yield self._simple_call_without_pop_reply(command, *args)
        reply = None
        for _ in args:
            reply = yield self._reply_queue_get()
            if reply is None or len(reply) != 3 or \
               reply[0].lower() != command.lower():
                raise tornado.gen.Return(False)
        if reply is not None and reply[2] == 0:
            self.subscribed = False
        raise tornado.gen.Return(True)

    @tornado.gen.coroutine
    def pubsub_pop_message(self, deadline=None):
        if not self.subscribed:
            raise ClientError("you must subcribe before using "
                              "pubsub_pop_message")
        try:
            pop = self._reply_queue_get
            reply = yield pop(deadline=deadline,
                              raise_exception_for_timeout=False)
        except toro.Timeout:
            reply = None
        raise tornado.gen.Return(reply)

    @tornado.gen.coroutine
    def _reply_queue_get(self, deadline=None,
                         raise_exception_for_timeout=True):
        reply = yield self.__reply_queue.get(deadline=deadline)
        if isinstance(reply, StopObject):
            raise ConnectionError("connection to redis closed by the server")
        if raise_exception_for_timeout and reply is None:
            self.__connection.disconnect()
            raise ConnectionError("read timeout")
        raise tornado.gen.Return(reply)

    @tornado.gen.coroutine
    def _pipelined_call(self, pipeline):
        buf = io.BytesIO()
        for args in pipeline.pipelined_args:
            msg = format_args_in_redis_protocol(*args)
            buf.write(msg)
        yield self.__connection.write(buf.getvalue())
        buf.close()
        result = []
        while len(result) < pipeline.number_of_stacked_calls:
            reply = yield self._reply_queue_get()
            result.append(reply)
        raise tornado.gen.Return(result)
