#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of tornadis library released under the MIT license.
# See the LICENSE file for more information.

import tornado.gen
import tornado.locks
import hiredis
import collections
import functools
import logging

from tornadis.connection import Connection
from tornadis.pipeline import Pipeline
from tornadis.utils import format_args_in_redis_protocol
from tornadis.write_buffer import WriteBuffer
from tornadis.exceptions import ConnectionError, ClientError


LOG = logging.getLogger(__name__)


def discard_reply_cb(reply):
    pass


class Client(object):
    """High level object to interact with redis.

    Attributes:
        autoconnect (boolean): True if the client is in autoconnect mode
            (and in autoreconnection mode) (default True).
        password (string): the password to authenticate with.
        connection_kwargs (dict): :class:`Connection` object
            kwargs (note that read_callback and close_callback args are
            set automatically).
    """

    def __init__(self, autoconnect=True, password=None, **connection_kwargs):
        """Constructor.

        Args:
            autoconnect (boolean): True if the client is in autoconnect mode
                (and in autoreconnection mode) (default True).
            password (string): the password to authenticate with.
            **connection_kwargs: :class:`Connection` object kwargs.
        """
        if 'read_callback' in connection_kwargs or \
                'close_callback' in connection_kwargs:
            raise Exception("read_callback and close_callback are not allowed "
                            "to be used here.")
        self.connection_kwargs = connection_kwargs
        self.autoconnect = autoconnect
        self.password = password
        self.__connection = None
        self.subscribed = False
        self.__connection = None
        self.__reader = None
        # Used for normal clients
        self.__callback_queue = None
        # Used for subscribed clients
        self._condition = tornado.locks.Condition()
        self._reply_list = None

    @property
    def title(self):
        return self.__connection._redis_server()

    def is_connected(self):
        """Returns True is the client is connected to redis.

        Returns:
            True if the client if connected to redis.
        """
        return (self.__connection is not None) and \
               (self.__connection.is_connected())

    @tornado.gen.coroutine
    def connect(self):
        """Connects the client object to redis.

        It's safe to use this method even if you are already connected.
        Note: this method is useless with autoconnect mode (default).

        Returns:
            a Future object with True as result if the connection was ok.
        """
        if self.is_connected():
            raise tornado.gen.Return(True)
        cb1 = self._read_callback
        cb2 = self._close_callback
        self.__callback_queue = collections.deque()
        self._reply_list = []
        self.__reader = hiredis.Reader(replyError=ClientError)
        kwargs = self.connection_kwargs
        self.__connection = Connection(cb1, cb2, **kwargs)
        connection_status = yield self.__connection.connect()
        if connection_status is not True or not self.password:
            # nothing left to do here, return
            raise tornado.gen.Return(connection_status)
        authentication_status = yield self._call('AUTH', self.password)
        if authentication_status == b'OK':
            # correct password, it worked
            raise tornado.gen.Return(True)
        else:
            # incorrect password, return back the result
            LOG.warning("impossible to connect: bad password")
            self.__connection.disconnect()
            raise tornado.gen.Return(False)

    def disconnect(self):
        """Disconnects the client object from redis.

        It's safe to use this method even if you are already disconnected.
        """
        if not self.is_connected():
            return
        if self.__connection is not None:
            self.__connection.disconnect()

    def _close_callback(self):
        """Callback called when redis closed the connection.

        The callback queue is emptied and we call each callback found
        with None or with an exception object to wake up blocked client.
        """
        while True:
            try:
                callback = self.__callback_queue.popleft()
                callback(ConnectionError("closed connection"))
            except IndexError:
                break
        if self.subscribed:
            # pubsub clients
            self._reply_list.append(ConnectionError("closed connection"))
            self._condition.notify_all()

    def _read_callback(self, data=None):
        """Callback called when some data are read on the socket.

        The buffer is given to the hiredis parser. If a reply is complete,
        we put the decoded reply to on the reply queue.

        Args:
            data (str): string (buffer) read on the socket.
        """
        try:
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
        except hiredis.ProtocolError:
            # something nasty occured (corrupt stream => no way to recover)
            LOG.warning("corrupted stream => disconnect")
            self.disconnect()

    def call(self, *args, **kwargs):
        """Calls a redis command and returns a Future of the reply.

        Args:
            *args: full redis command as variable length argument list or
                a Pipeline object (as a single argument).
            **kwargs: internal private options (do not use).

        Returns:
            a Future with the decoded redis reply as result (when available) or
                a ConnectionError object in case of connection error.

        Raises:
            ClientError: your Pipeline object is empty.

        Examples:

            >>> @tornado.gen.coroutine
                def foobar():
                    client = Client()
                    result = yield client.call("HSET", "key", "field", "val")
        """
        if not self.is_connected():
            if self.autoconnect:
                # We use this method only when we are not contected
                # to void performance penaly due to gen.coroutine decorator
                return self._call_with_autoconnect(*args, **kwargs)
            else:
                error = ConnectionError("you are not connected and "
                                        "autoconnect=False")
                return tornado.gen.maybe_future(error)
        return self._call(*args, **kwargs)

    @tornado.gen.coroutine
    def _call_with_autoconnect(self, *args, **kwargs):
        yield self.connect()
        if not self.is_connected():
            raise tornado.gen.Return(ConnectionError("impossible to connect"))
        res = yield self._call(*args, **kwargs)
        raise tornado.gen.Return(res)

    def async_call(self, *args, **kwargs):
        """Calls a redis command, waits for the reply and call a callback.

        Following options are available (not part of the redis command itself):

        - callback
            Function called (with the result as argument) when the result
            is available. If not set, the reply is silently discarded. In
            case of errors, the callback is called with a
            TornadisException object as argument.

        Args:
            *args: full redis command as variable length argument list or
                a Pipeline object (as a single argument).
            **kwargs: options as keyword parameters.

        Examples:

            >>> def cb(result):
                    pass
            >>> client.async_call("HSET", "key", "field", "val", callback=cb)
        """
        def after_autoconnect_callback(future):
            if self.is_connected():
                self._call(*args, **kwargs)
            else:
                # FIXME
                pass

        if 'callback' not in kwargs:
            kwargs['callback'] = discard_reply_cb
        if not self.is_connected():
            if self.autoconnect:
                connect_future = self.connect()
                cb = after_autoconnect_callback
                self.__connection._ioloop.add_future(connect_future, cb)
            else:
                error = ConnectionError("you are not connected and "
                                        "autoconnect=False")
                kwargs['callback'](error)
        else:
            self._call(*args, **kwargs)

    def _call(self, *args, **kwargs):
        callback = False
        if 'callback' in kwargs:
            callback = True
        if len(args) == 1 and isinstance(args[0], Pipeline):
            fn = self._pipelined_call
            pipeline = args[0]
            if pipeline.number_of_stacked_calls == 0:
                excep = ClientError("empty pipeline")
                if callback:
                    kwargs['callback'](excep)
                else:
                    return tornado.gen.maybe_future(excep)
            arguments = (pipeline,)
        else:
            if "__multiple_replies" in kwargs:
                fn = self._simple_call_with_multiple_replies
                arguments = tuple([kwargs["__multiple_replies"]] + list(args))
            else:
                fn = self._simple_call
                arguments = args
        if callback:
            fn(*arguments, **kwargs)
        else:
            return tornado.gen.Task(fn, *arguments, **kwargs)

    def _reply_aggregator(self, callback, replies, reply):
        self._reply_list.append(reply)
        if len(self._reply_list) == replies:
            callback(self._reply_list)
            self._reply_list = []

    def _simple_call(self, *args, **kwargs):
        callback = kwargs['callback']
        msg = format_args_in_redis_protocol(*args)
        self.__callback_queue.append(callback)
        self.__connection.write(msg)

    def _simple_call_with_multiple_replies(self, replies, *args, **kwargs):
        original_callback = kwargs['callback']
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
