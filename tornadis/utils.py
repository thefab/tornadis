#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of tornadis library released under the MIT license.
# See the LICENSE file for more information.


import six
from tornado.concurrent import Future
import contextlib
import collections


class WriteBuffer(object):
    """Write buffer implementation optimized for reading by max sized chunks.

    It is built on a deque and memoryviews to avoid too much string copies.

    Attributes:
        use_memory_view_min_size (int): minimum size before using memoryview
            objects (to avoid object creation overhead bigger than string
            copy for this size)
        _deque (collections.deque): deque object to store each write
            (without copy)
        _has_view (boolean): True if there is some memoryview objects inside
            the deque (if _has_view=False, there are some
            "fastpath optimizations")
        _total_length (int): total size (in bytes) of the buffer content
    """

    def __init__(self, use_memory_view_min_size=4096):
        """Constructor.

        Args:
            use_memory_view_min_size (int): minimum size before using
                memoryview objects (advanced option, the default is probably
                good for you).
        """
        self.use_memory_view_min_size = use_memory_view_min_size
        self._deque = collections.deque()
        self._reset()

    def _reset(self):
        """Resets the object at its initial (empty) state."""
        self._deque.clear()
        self._total_length = 0
        self._has_view = False

    def __str__(self):
        return self._tobytes()

    def __bytes__(self):
        return self._tobytes()

    def _tobytes(self):
        """Serializes the write buffer into a single string (bytes).

        Returns:
            a string (bytes) object.
        """
        if not self._has_view:
            # fast path optimization
            if len(self._deque) == 0:
                return b""
            elif len(self._deque) == 1:
                # no copy
                return self._deque[0]
            else:
                return b"".join(self._deque)
        else:
            tmp = [x.tobytes() if isinstance(x, memoryview) else x
                   for x in self._deque]
            return b"".join(tmp)

    def is_empty(self):
        """Returns True if the buffer is empty.

        Returns:
            True or False.
        """
        return self._total_length == 0

    def append(self, data):
        """Appends some data to end of the buffer (right).

        No string copy is done during this operation.

        Args:
            data: data to put in the buffer (can be string, memoryview or
                another WriteBuffer).
        """
        self._append(data, True)

    def appendleft(self, data):
        """Appends some data at the beginning of the buffer (left).

        No string copy is done during this operation.

        Args:
            data: data to put in the buffer (can be string, memoryview or
                another WriteBuffer).
        """
        self._append(data, False)

    def _append(self, data, right):
        if isinstance(data, WriteBuffer):
            # data is another writebuffer
            if right:
                self._deque.extend(data._deque)
            else:
                self._deque.extendleft(data._deque)
            self._total_length += data._total_length
            self._has_view = self._has_view and data._has_view
        else:
            length = len(data)
            if length == 0:
                return
            if isinstance(data, memoryview):
                # data is a memory viewobject
                # nothing spacial but now the buffer has views
                self._has_view = True
            self._total_length += length
            if right:
                self._deque.append(data)
            else:
                self._deque.appendleft(data)

    def get_pointer_or_memoryview(self, data, data_length):
        """Gets a reference on the data object or a memoryview on it.

        Utility method, the use of memoryview (or not) depends on data_length
        and self.use_memory_view_min_size.

        Args:
            data: string of memoryview.
            data_length: length of data arg.

        Returns:
            A reference on data object or a memoryview on it.
        """
        if data_length < self.use_memory_view_min_size \
           or isinstance(data, memoryview):
            return data
        else:
            return memoryview(data)

    def get_chunk(self, chunk_max_size):
        """Gets a chunk of the given max size.

        Optimized to avoid too much string copies.

        Args:
            chunk_max_size (int): max size of the returned chunk.

        Returns:
            string (bytes) with a size <= chunk_max_size.
        """
        if self._total_length < chunk_max_size:
            # fastpath (the whole queue fit in a single chunk)
            res = self._tobytes()
            self._reset()
            return res
        first_iteration = True
        while True:
            try:
                data = self._deque.popleft()
                data_length = len(data)
                self._total_length -= data_length
                if first_iteration:
                    # first iteration
                    if data_length == chunk_max_size:
                        # we are lucky !
                        return data
                    elif data_length > chunk_max_size:
                        # we have enough data at first iteration
                        # => fast path optimization
                        view = self.get_pointer_or_memoryview(data,
                                                              data_length)
                        self.appendleft(view[chunk_max_size:])
                        return view[:chunk_max_size]
                    else:
                        # no single iteration fast path optimization :-(
                        # let's use a WriteBuffer to build the result chunk
                        chunk_write_buffer = WriteBuffer()
                else:
                    # not first iteration
                    if chunk_write_buffer._total_length + data_length \
                       > chunk_max_size:
                        view = self.get_pointer_or_memoryview(data,
                                                              data_length)
                        limit = chunk_max_size - \
                            chunk_write_buffer._total_length - data_length
                        self.appendleft(view[limit:])
                        data = view[:limit]
                chunk_write_buffer.append(data)
                if chunk_write_buffer._total_length >= chunk_max_size:
                    break
            except IndexError:
                # the buffer is empty (so no memoryview inside)
                self._has_view = False
                break
            first_iteration = False
        return chunk_write_buffer._tobytes()


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
        Future.__init__(self)
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
