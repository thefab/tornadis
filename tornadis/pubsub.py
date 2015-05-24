#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of tornadis library released under the MIT license.
# See the LICENSE file for more information.

import tornado.ioloop
import tornado.gen
import toro
import logging

from tornadis.client import Client
from tornadis.exceptions import ConnectionError, ClientError

LOG = logging.getLogger()


class PubSubClient(Client):
    """High level specific object to interact with pubsub redis.

    The call() method is forbidden with this object.

    More informations on the redis side: http://redis.io/topics/pubsub

    Attributes:
        host (string): the host name to connect to.
        port (int): the port to connect to.
        read_page_size (int): page size for reading.
        write_page_size (int): page size for writing.
        connect_timeout (int): timeout (in seconds) for connecting.
        subscribed (boolean): True if the client is in subscription mode.
    """

    def call(self, *args, **kwargs):
        raise ClientError("not allowed with PubSubClient object")

    def async_call(self, *args, **kwargs):
        raise ClientError("not allowed with PubSubClient object")

    def pubsub_subscribe(self, *args):
        """Subscribes to a list of channels.

        http://redis.io/topics/pubsub

        Args:
            *args: variable list of channels to subscribe.

        Returns:
            Future: Future with True as result if the subscribe is ok.

        Examples:

            >>> yield client.pubsub_subscribe("channel1", "channel2")
        """
        return self._pubsub_subscribe(b"SUBSCRIBE", *args)

    def pubsub_psubscribe(self, *args):
        """Subscribes to a list of patterns.

        http://redis.io/topics/pubsub

        Args:
            *args: variable list of patterns to subscribe.

        Returns:
            Future: Future with True as result if the subscribe is ok.

        Examples:

            >>> yield client.pubsub_psubscribe("channel*", "foo*")
        """
        return self._pubsub_subscribe(b"PSUBSCRIBE", *args)

    @tornado.gen.coroutine
    def _pubsub_subscribe(self, command, *args):
        results = yield Client.call(self, command, *args,
                                    __multiple_replies=len(args))
        for reply in results:
            if isinstance(reply, ConnectionError) or len(reply) != 3 or \
                    reply[0].lower() != command.lower() or reply[2] == 0:
                raise tornado.gen.Return(False)
        self.subscribed = True
        raise tornado.gen.Return(True)

    def pubsub_unsubscribe(self, *args):
        """Unsubscribes from a list of channels.

        http://redis.io/topics/pubsub

        Args:
            *args: variable list of channels to unsubscribe.

        Returns:
            Future: Future with True as result if the unsubscribe is ok.

        Examples:

            >>> yield client.pubsub_unsubscribe("channel1", "channel2")
        """
        return self._pubsub_unsubscribe(b"UNSUBSCRIBE", *args)

    def pubsub_punsubscribe(self, *args):
        """Unsubscribes from a list of patterns.

        http://redis.io/topics/pubsub

        Args:
            *args: variable list of patterns to unsubscribe.

        Returns:
            Future: Future with True as result if the unsubscribe is ok.

        Examples:

            >>> yield client.pubsub_punsubscribe("channel*", "foo*")

        """
        return self._pubsub_unsubscribe(b"PUNSUBSCRIBE", *args)

    @tornado.gen.coroutine
    def _pubsub_unsubscribe(self, command, *args):
        results = yield Client.call(self, command, *args,
                                    __multiple_replies=len(args))
        for reply in results:
            if isinstance(reply, ConnectionError) or len(reply) != 3 or \
                    reply[0].lower() != command.lower():
                raise tornado.gen.Return(False)
            if reply[2] == 0:
                self.subscribed = False
        raise tornado.gen.Return(True)

    @tornado.gen.coroutine
    def pubsub_pop_message(self, deadline=None):
        """Pops a message for a subscribed client.

        Args:
            deadline (int): max number of seconds to wait (None => no timeout)

        Returns:
            Future with the popped message as result (or None if timeout
                or ConnectionError object in case of connection errors).

        Raises:
            ClientError: when you are not subscribed to anything
        """
        if not self.subscribed:
            raise ClientError("you must subscribe before using "
                              "pubsub_pop_message")
        reply = None
        try:
            try:
                reply = self._reply_list.pop(0)
            except IndexError:
                yield self._condition.wait(deadline=deadline)
        except toro.Timeout:
            pass
        else:
            if reply is None:
                try:
                    reply = self._reply_list.pop(0)
                except IndexError:
                    pass
        raise tornado.gen.Return(reply)
