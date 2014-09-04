#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of tornadis library released under the MIT license.
# See the LICENSE file for more information.

import tornado.gen
import toro
from collections import deque

from tornadis.client import Client

# FIXME: error handling


class ClientPool(object):

    max_size = None
    client_kwargs = None
    read_callback = None
    __sem = None
    __pool = None

    def __init__(self, max_size=-1, **kwargs):
        self.max_size = max_size
        self.client_kwargs = kwargs
        self.__pool = deque()
        if self.max_size != -1:
            self.__sem = toro.Semaphore(self.max_size)

    @tornado.gen.coroutine
    def get_connected_client(self):
        if self.__sem is not None:
            yield self.__sem.acquire()
        try:
            client = self.__pool.popleft()
        except IndexError:
            client = self._make_client()
            yield client.connect()
        raise tornado.gen.Return(client)

    def release_client(self, client):
        self.__pool.append(client)
        if self.__sem is not None:
            self.__sem.release()

    def destroy(self):
        while True:
            try:
                client = self.__pool.popleft()
                client.disconnect()
            except IndexError:
                break

    def _make_client(self):
        kwargs = self.client_kwargs
        client = Client(**kwargs)
        return client
