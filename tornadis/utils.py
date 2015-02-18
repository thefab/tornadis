#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of tornadis library released under the MIT license.
# See the LICENSE file for more information.


import six
from tornado.concurrent import Future
import contextlib
import collections

WRITEBUFFER_USE_MEMORY_VIEW_MIN_SIZE = 4096


class WriteBuffer(object):

    def __init__(self):
        self._deque = collections.deque()
        self._total_length = 0
        self._has_view = False

    def __str__(self):
        return self._tobytes(self._deque)

    def __bytes__(self):
        return self._tobytes(self._deque)

    def _tobytes(self, iterable):
        if not self._has_view:
            # fast path
            return b"".join(iterable)
        else:
            tmp = [x.tobytes() if isinstance(x, memoryview) else x
                   for x in iterable]
            return b"".join(tmp)

    def is_empty(self):
        return self._total_length == 0

    def append(self, data, right=True):
        length = len(data)
        if length == 0:
            return
        self._total_length += length
        if right:
            self._deque.append(data)
        else:
            self._deque.appendleft(data)

    def extend(self, write_buffer):
        self._deque.extend(write_buffer._deque)
        self._total_length += write_buffer._total_length

    def appendleft(self, data):
        self.append(data, right=False)

    def get_chunk(self, chunk_max_size):
        if self._total_length < chunk_max_size:
            # fastpath (the whole queue fit in a single chunk)
            res = self._tobytes(self._deque)
            self._deque.clear()
            self._has_view = False
            self._total_length = 0
            return res
        chunk_size = 0
        tmp_list = []
        while True:
            try:
                data = self._deque.popleft()
                data_length = len(data)
                self._total_length -= data_length
                if chunk_size == 0:
                    # first iteration
                    if data_length == chunk_max_size:
                        return data
                    elif data_length > chunk_max_size:
                        if data_length < WRITEBUFFER_USE_MEMORY_VIEW_MIN_SIZE \
                           or isinstance(data, memoryview):
                            view = data
                        else:
                            view = memoryview(data)
                        self._has_view = True
                        self.appendleft(view[chunk_max_size:])
                        return view[:chunk_max_size]
                else:
                    # not first iteration
                    if chunk_size + data_length > chunk_max_size:
                        if data_length < WRITEBUFFER_USE_MEMORY_VIEW_MIN_SIZE \
                           or isinstance(data, memoryview):
                            view = data
                        else:
                            view = memoryview(data)
                        self._has_view = True
                        limit = chunk_max_size - chunk_size - data_length
                        self.appendleft(view[limit:])
                        data = view[:limit]
                tmp_list.append(data)
                chunk_size += data_length
                if chunk_size >= chunk_max_size:
                    break
            except IndexError:
                self.has_view = False
                break
        return self._tobytes(tmp_list)


def format_args_in_redis_protocol(*args):
    """Formats arguments into redis protocol...

    This function makes and returns a string/buffer corresponding to
    given arguments formated with the redis protocol.

    integer, text, string or binary types are automatically converted
    (using utf8 if necessary).

    More informations about the protocol: http://redis.io/topics/protocol

    Args:
        *args: full redis command as variable length argument list

    Returns:
        binary string (arguments in redis protocol)

    Examples:
        >>> format_args_in_redis_protocol("HSET", "key", "field", "value")
        '*4\r\n$4\r\nHSET\r\n$3\r\nkey\r\n$5\r\nfield\r\n$5\r\nvalue\r\n'
    """
    buf = WriteBuffer()
    l = "*%d\r\n" % len(args)
    if six.PY2:
        buf.append(l)
    else:  # pragma: no cover
        buf.append(l.encode('utf-8'))
    for arg in args:
        if isinstance(arg, six.text_type):
            # it's a unicode string in Python2 or a un standard (unicode)
            # string in Python3, let's encode it in utf-8 to get raw bytes
            arg = arg.encode('utf-8')
        elif isinstance(arg, six.string_types):
            # it's a basestring in Python2 => nothing to do
            pass
        elif isinstance(arg, six.binary_type):  # pragma: no cover
            # it's a raw bytes string in Python3 => nothing to do
            pass
        elif isinstance(arg, six.integer_types):
            tmp = "%d" % arg
            if six.PY2:
                arg = tmp
            else:  # pragma: no cover
                arg = tmp.encode('utf-8')
        else:
            raise Exception("don't know what to do with %s" % type(arg))
        l = "$%d\r\n" % len(arg)
        if six.PY2:
            buf.append(l)
        else:  # pragma: no cover
            buf.append(l.encode('utf-8'))
        buf.append(arg)
        buf.append(b"\r\n")
    return buf


class ContextManagerFuture(Future):
    """A Future that can be used with the "with" statement.

    When a coroutine yields this Future, the return value is a context manager
    that can be used like:

        >>> with (yield future) as result:
                pass

    At the end of the block, the Future's exit callback is run.

    This class is stolen from "toro" source:
    https://github.com/ajdavis/toro/blob/master/toro/__init__.py

    Original credits to jesse@mongodb.com
    Modified to be able to return the future result

    Attributes:
        _exit_callback (callable): the exit callback to call at the end of
            the block
        _wrapped (Future): the wrapped future
    """
    def __init__(self, wrapped, exit_callback):
        """Constructor.

        Args:
            wrapped (Future): the original Future object (to wrap)
            exit_callback: the exit callback to call at the end of
                the block
        """
        super(ContextManagerFuture, self).__init__()
        wrapped.add_done_callback(self._done_callback)
        self._exit_callback = exit_callback
        self._wrapped = wrapped

    def _done_callback(self, wrapped):
        """Internal "done callback" to set the result of the object.

        The result of the object if forced by the wrapped future. So this
        internal callback must be called when the wrapped future is ready.

        Args:
            wrapped (Future): the wrapped Future object
        """
        if wrapped.exception():
            self.set_exception(wrapped.exception())
        else:
            self.set_result(wrapped.result())

    def result(self):
        """The result method which returns a context manager

        Returns:
            ContextManager: The corresponding context manager
        """
        if self.exception():
            raise self.exception()
        # Otherwise return a context manager that cleans up after the block.

        @contextlib.contextmanager
        def f():
            try:
                yield self._wrapped.result()
            finally:
                self._exit_callback()
        return f()


class StopObject(object):
    """Dummy object just to have a specific type to test."""

    pass
