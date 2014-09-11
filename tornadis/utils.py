#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of tornadis library released under the MIT license.
# See the LICENSE file for more information.


import six
from tornado.concurrent import Future
import contextlib


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
    l = "*%d" % len(args)
    if six.PY2:
        lines = [l]
    else:  # pragma: no cover
        lines = [l.encode('utf-8')]
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
        l = "$%d" % len(arg)
        if six.PY2:
            lines.append(l)
        else:  # pragma: no cover
            lines.append(l.encode('utf-8'))
        lines.append(arg)
    lines.append(b"")
    return b"\r\n".join(lines)


# This class is "stolen" from here:
# https://github.com/ajdavis/toro/blob/master/toro/__init__.py
# Original credits to jesse@mongodb.com
# Modified to be able to return the future result
class ContextManagerFuture(Future):
    """A Future that can be used with the "with" statement.
    When a coroutine yields this Future, the return value is a context manager
    """
    def __init__(self, wrapped, exit_callback):
        super(ContextManagerFuture, self).__init__()
        wrapped.add_done_callback(self._done_callback)
        self.exit_callback = exit_callback
        self.wrapped = wrapped

    def _done_callback(self, wrapped):
        if wrapped.exception():
            self.set_exception(wrapped.exception())
        else:
            self.set_result(wrapped.result())

    def result(self):
        if self.exception():
            raise self.exception()
        # Otherwise return a context manager that cleans up after the block.

        @contextlib.contextmanager
        def f():
            try:
                yield self.wrapped.result()
            finally:
                self.exit_callback()
        return f()
