#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of tornadis library released under the MIT license.
# See the LICENSE file for more information.

import tornado.gen
import toro
import functools
from collections import deque

from tornadis.client import Client
from tornadis.utils import ContextManagerFuture

# FIXME: error handling


class ClientPool(object):
    """High level object to deal with a pool of redis clients

    Attributes:
        client_kwargs (dict): Client constructor arguments
        __sem (toro.Semaphore): Semaphore object to deal with pool limits
            (only when max_size != -1)
        __pool (deque): double-ended queue which contains pooled client objets
    """

    def __init__(self, max_size=-1, **client_kwargs):
        """Constructor.

        Args:
            max_size (int): max size of the pool (-1 means "no limit")
                (dict): Client constructor arguments
            client_kwargs (dict): Client constructor arguments
        """
        self.max_size = max_size
        self.client_kwargs = client_kwargs
        self.__pool = deque()
        if self.max_size != -1:
            self.__sem = toro.Semaphore(self.max_size)
        else:
            self.__sem = None

    @tornado.gen.coroutine
    def get_connected_client(self):
        """Gets a connected Client object.

        If max_size is reached, this method will block until a new client
        object is available.

        Returns:
            A Future object with connected Client instance as a result.
        """
        if self.__sem is not None:
            yield self.__sem.acquire()
        try:
            client = self.__pool.popleft()
        except IndexError:
            client = self._make_client()
            yield client.connect()
        raise tornado.gen.Return(client)

    def connected_client(self):
        future = self.get_connected_client()
        cb = functools.partial(self._connected_client_release_cb, future)
        return ContextManagerFuture(future, cb)

    def _connected_client_release_cb(self, future=None):
        client = future.result()
        self.release_client(client)

    def release_client(self, client):
        """Releases a client object to the pool.

        Args:
            client: Client object
        """
        self.__pool.append(client)
        if self.__sem is not None:
            self.__sem.release()

    def destroy(self):
        """Disconnects all pooled client objects."""
        while True:
            try:
                client = self.__pool.popleft()
                client.disconnect()
            except IndexError:
                break

    def _make_client(self):
        """Makes and returns a Client object."""
        kwargs = self.client_kwargs
        client = Client(**kwargs)
        return client
