#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of tornadis library released under the MIT license.
# See the LICENSE file for more information.

DEFAULT_HOST = '127.0.0.1'
DEFAULT_PORT = 6379
DEFAULT_CONNECT_TIMEOUT = 20
DEFAULT_READ_PAGE_SIZE = 65536
DEFAULT_WRITE_PAGE_SIZE = 65536

from tornadis.utils import WriteBuffer
from tornadis.client import Client
from tornadis.pubsub import PubSubClient
from tornadis.pool import ClientPool
from tornadis.pipeline import Pipeline
from tornadis.exceptions import ConnectionError, ClientError

__all__ = ['Client', 'ClientPool', 'Pipeline',
           'ConnectionError', 'ClientError', 'PubSubClient', 'WriteBuffer']
