#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of tornadis library released under the MIT license.
# See the LICENSE file for more information.

version_info = (0, 1, 0)
__version__ = ".".join([str(x) for x in version_info])

DEFAULT_HOST = '127.0.0.1'
DEFAULT_PORT = 6379
DEFAULT_CONNECT_TIMEOUT = 20
DEFAULT_READ_PAGE_SIZE = 65536
DEFAULT_WRITE_PAGE_SIZE = 65536

from tornadis.client import Client
from tornadis.pubsub import PubSubClient
from tornadis.pool import ClientPool
from tornadis.pipeline import Pipeline
from tornadis.exceptions import TornadisException, ConnectionError, ClientError

__all__ = ['Client', 'ClientPool', 'Pipeline', 'TornadisException',
           'ConnectionError', 'ClientError', 'PubSubClient']
