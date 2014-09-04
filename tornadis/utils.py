#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of tornadis library released under the MIT license.
# See the LICENSE file for more information.


import six


def format_args_in_redis_protocol(*args):
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
        elif isinstance(arg, six.binary_type):
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
