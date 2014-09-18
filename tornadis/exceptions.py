#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of tornadis library released under the MIT license.
# See the LICENSE file for more information.


class TornadisException(Exception):
    """Base Exception class."""
    pass


class ConnectionError(TornadisException):
    """Exception raised when there is a connection error."""
    pass


class ClientError(TornadisException):
    """Exception raised when there is a client error."""
