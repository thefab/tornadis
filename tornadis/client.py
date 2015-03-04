#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of tornadis library released under the MIT license.
# See the LICENSE file for more information.

import tornado.ioloop
import tornado.gen
import hiredis
import logging
import collections
import functools
import toro

from tornadis.connection import Connection
from tornadis.pipeline import Pipeline
from tornadis.utils import format_args_in_redis_protocol, StopObject
from tornadis.write_buffer import WriteBuffer
from tornadis.exceptions import ConnectionError, ClientError
import tornadis

LOG = logging.getLogger()


class Client(object):
    """High level object to interact with redis.

    Attributes:
        host (string): the host name to connect to.
        port (int): the port to connect to.
        read_page_size (int): page size for reading.
        write_page_size (int): page size for writing.
        connect_timeout (int): timeout (in seconds) for connecting.
        subscribed (boolean): True if the client is in subscription mode.
    """

    def __init__(self, host=tornadis.DEFAULT_HOST, port=tornadis.DEFAULT_PORT,
                 read_page_size=tornadis.DEFAULT_READ_PAGE_SIZE,
                 write_page_size=tornadis.DEFAULT_WRITE_PAGE_SIZE,
                 connect_timeout=tornadis.DEFAULT_CONNECT_TIMEOUT,
                 ioloop=None):
        """Constructor.

        Args:
            host (string): the host name to connect to.
            port (int): the port to connect to.
            read_page_size (int): page size for reading.
            write_page_size (int): page size for writing.
            connect_timeout (int): timeout (in seconds) for connecting.
            ioloop (IOLoop): the tornado ioloop to use.
        """
        self.host = host
        self.port = port
        self.read_page_size = read_page_size
        self.write_page_size = write_page_size
        self.connect_timeout = connect_timeout
        self.__ioloop = ioloop or tornado.ioloop.IOLoop.instance()
        self.__connection = None
        self.subscribed = False
        self.__connection = None
        self.__reader = None
        # Used for normal clients
        self.__callback_queue = None
        # Used for subscribed clients
        self._condition = toro.Condition()
        self._reply_list = None

    def is_connected(self):
        """Returns True is the client is connected to redis.

        Returns:
            True if the client if connected to redis.
        """
        return (self.__connection is not None) and \
               (self.__connection.is_connected())

    def connect(self):
        """Connects the client object to redis.

        Returns:
            a Future object with no result.

        Raises:
            ConnectionError: when there is a connection error.
            ClientError: when you are already connected.
        """
        if self.is_connected():
            raise ClientError("you are already connected")
        cb1 = self._read_callback
        cb2 = self._close_callback
        self.__callback_queue = collections.deque()
        self._reply_list = []
        self.__reader = hiredis.Reader()
        self.__connection = Connection(cb1, cb2, host=self.host,
                                       port=self.port, ioloop=self.__ioloop,
                                       read_page_size=self.read_page_size,
                                       write_page_size=self.write_page_size,
                                       connect_timeout=self.connect_timeout)
        return self.__connection.connect()

    def disconnect(self):
        """Disconnects the client object from redis.

        It's safe to use this method even if you are already disconnected.

        Returns:
            a Future object with undetermined result.
        """
        if not self.is_connected():
            return
        try:
            return tornado.gen.Task(self._simple_call, "QUIT")
        except ConnectionError:
            if self.__connection is not None:
                self.__connection.disconnect()

    def _close_callback(self):
        """Callback called when redis closed the connection.

        The callback queue is emptied and we call each callback found
        with a special "StopObject" to wake up blocked client.
        """
        while True:
            try:
                callback = self.__callback_queue.popleft()
                callback(StopObject())
            except IndexError:
                break

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
                    try:
                        callback = self.__callback_queue.popleft()
                        # normal client (1 reply = 1 callback)
                        callback(reply)
                    except IndexError:
                        # pubsub clients
                        self._reply_list.append(reply)
                        self._condition.notify_all()
                else:
                    break

    def call(self, *args, **kwargs):
        """Calls a redis command and waits for the reply.

        Following options are available (not part of the redis command itself):

        - callback
            Function called (with the result as argument) when the
            future resolves (standard behavior of the tornado.gen.coroutine
            decorator => do not yield the returned Future when you use a
            callback argument).
        - discard_reply
            If True (default False), don't wait for completion
            and discard the reply (when it becomes available) => do not
            yield the returned Future and don't use together with callback
            option.

        Args:
            *args: full redis command as variable length argument list.
            **kwargs: options as keyword parameters.

        Returns:
            a Future with the decoded redis reply as result.

        Raises:
            ClientError: you are not connected.

        Examples:

            >>> @tornado.gen.coroutine
                def foobar():
                    client = Client()
                    result = yield client.call("HSET", "key", "field", "val")

            >>> client.call("HSET", "key", "field", "val", discard_reply=True)
        """
        if not self.is_connected():
            raise ClientError("you are not connected")
        discard = False
        callback = False
        if 'discard_reply' in kwargs:
            discard = True
            kwargs.pop('discard_reply')
        if 'callback' in kwargs:
            callback = True
            if discard:
                raise ClientError("Don't use callback and "
                                  "discard_reply together")
        if len(args) == 1 and isinstance(args[0], Pipeline):
            fn = self._pipelined_call
            arguments = (args[0],)
        else:
            fn = self._simple_call
            arguments = args
        if discard or callback:
            fn(*arguments, **kwargs)
        else:
            return tornado.gen.Task(fn, *arguments, **kwargs)

    def _discard_reply(self, reply):
        pass

    def _reply_aggregator(self, callback, replies, reply):
        self._reply_list.append(reply)
        if len(self._reply_list) == replies:
            callback(self._reply_list)
            self._reply_list = []

    def _simple_call(self, *args, **kwargs):
        callback = kwargs.get('callback', self._discard_reply)
        msg = format_args_in_redis_protocol(*args)
        self.__callback_queue.append(callback)
        self.__connection.write(msg)

    def _simple_call_with_multiple_replies(self, replies, *args, **kwargs):
        original_callback = kwargs.get('callback', self._discard_reply)
        msg = format_args_in_redis_protocol(*args)
        callback = functools.partial(self._reply_aggregator, original_callback,
                                     replies)
        for _ in range(0, replies):
            self.__callback_queue.append(callback)
        self.__connection.write(msg)

    def _pipelined_call(self, pipeline, callback):
        buf = WriteBuffer()
        replies = len(pipeline.pipelined_args)
        cb = functools.partial(self._reply_aggregator, callback, replies)
        for args in pipeline.pipelined_args:
            self.__callback_queue.append(cb)
            tmp_buf = format_args_in_redis_protocol(*args)
            buf.append(tmp_buf)
        self.__connection.write(buf)

    def get_last_state_change_timedelta(self):
        return self.__connection._state.get_last_state_change_timedelta()
