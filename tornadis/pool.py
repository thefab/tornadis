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
from tornadis.exceptions import ClientError


class ClientPool(object):
    """High level object to deal with a pool of redis clients.

    Attributes:
        max_size (int): max size of the pool (-1 means "no limit").
        client_timeout (int): timeout in seconds of a connection released
            to the pool (-1 means "no timeout").
        client_kwargs (dict): Client constructor arguments
    """

    def __init__(self, max_size=-1, client_timeout=-1, **client_kwargs):
        """Constructor.

        Args:
            max_size (int): max size of the pool (-1 means "no limit").
            client_timeout (int): timeout in seconds of a connection released
                to the pool (-1 means "no timeout").
            client_kwargs (dict): Client constructor arguments.
        """
        self.max_size = max_size
        self.client_timeout = client_timeout
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

        Raises:
            ConnectionError: when there is a connection error.
        """
        if self.__sem is not None:
            yield self.__sem.acquire()
        client = None
        try:
            while True:
                client = self.__pool.popleft()
                if client.is_connected():
                    if self._is_expired_client(client):
                        client.disconnect()
                        continue
                    break
        except IndexError:
            client = self._make_client()
            yield client.connect()
        raise tornado.gen.Return(client)

    def _is_expired_client(self, client):
        if self.client_timeout != -1 and client.is_connected():
            delta = client.get_last_state_change_timedelta()
            if delta.total_seconds() >= self.client_timeout:
                return True
        return False

    def connected_client(self):
        """Returns a ContextManagerFuture to be yielded in a with statement.

        Returns:
            A ContextManagerFuture object.

        Examples:
            >>> with (yield pool.connected_client()) as client:
                    # client is a connected tornadis.Client instance
                    # it will be automatically released to the pool thanks to
                    # the "with" keyword
                    reply = yield client.call("PING")
        """
        future = self.get_connected_client()
        cb = functools.partial(self._connected_client_release_cb, future)
        return ContextManagerFuture(future, cb)

    def _connected_client_release_cb(self, future=None):
        client = future.result()
        self.release_client(client)

    def release_client(self, client):
        """Releases a client object to the pool.

        Args:
            client: Client object.
        """
        if not self._is_expired_client(client):
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

    @tornado.gen.coroutine
    def preconnect(self, size=-1):
        """(pre)Connects some or all redis clients inside the pool.

        Args:
            size (int): number of redis clients to build and to connect
                (-1 means all clients if pool max_size > -1)

        Raises:
            ConnectionError: when there is a connection error.
            ClientError: when size == -1 and pool max_size == -1
        """
        if size == -1 and self.max_size == -1:
            raise ClientError("size=-1 not allowed with pool max_size=-1")
        limit = min(size, self.max_size) if size != -1 else self.max_size
        clients = yield [self.get_connected_client() for _ in range(0, limit)]
        for client in clients:
            self.release_client(client)

    def _make_client(self):
        """Makes and returns a Client object."""
        kwargs = self.client_kwargs
        client = Client(**kwargs)
        return client
