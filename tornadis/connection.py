#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of tornadis library released under the MIT license.
# See the LICENSE file for more information.

import socket
import os
import tornado.iostream
import tornado.gen
from tornado.util import errno_from_exception
from tornadis.write_buffer import WriteBuffer
from tornadis.state import ConnectionState
from tornado.ioloop import IOLoop
import tornadis
import errno
import logging

# Stolen from tornado/iostream.py
_ERRNO_WOULDBLOCK = (errno.EWOULDBLOCK, errno.EAGAIN)
if hasattr(errno, "WSAEWOULDBLOCK"):  # pragma: no cover
    _ERRNO_WOULDBLOCK += (errno.WSAEWOULDBLOCK,)
_ERRNO_CONNRESET = (errno.ECONNRESET, errno.ECONNABORTED, errno.EPIPE,
                    errno.ETIMEDOUT)
if hasattr(errno, "WSAECONNRESET"):  # pragma: no cover
    _ERRNO_CONNRESET += (errno.WSAECONNRESET, errno.WSAECONNABORTED,
                         errno.WSAETIMEDOUT)
_ERRNO_INPROGRESS = (errno.EINPROGRESS,)
if hasattr(errno, "WSAEINPROGRESS"):  # pragma: no cover
    _ERRNO_INPROGRESS += (errno.WSAEINPROGRESS,)

LOG = logging.getLogger(__name__)

READ_EVENT = IOLoop.READ
WRITE_EVENT = IOLoop.WRITE
ERROR_EVENT = IOLoop.ERROR


class Connection(object):
    """Low level connection object.

    Attributes:
        host (string): the host name to connect to.
        port (int): the port to connect to.
        unix_domain_socket (string): path to a unix socket to connect to
            (if set, overrides host/port parameters).
        read_page_size (int): page size for reading.
        write_page_size (int): page size for writing.
        connect_timeout (int): timeout (in seconds) for connecting.
        tcp_nodelay (boolean): set TCP_NODELAY on socket.
        aggressive_write (boolean): try to minimize write latency over
            global throughput (default False).
    """

    def __init__(self, read_callback, close_callback,
                 host=tornadis.DEFAULT_HOST,
                 port=tornadis.DEFAULT_PORT, unix_domain_socket=None,
                 read_page_size=tornadis.DEFAULT_READ_PAGE_SIZE,
                 write_page_size=tornadis.DEFAULT_WRITE_PAGE_SIZE,
                 connect_timeout=tornadis.DEFAULT_CONNECT_TIMEOUT,
                 tcp_nodelay=False, aggressive_write=False, ioloop=None):
        """Constructor.

        Args:
            read_callback: callback called when there is something to read.
            close_callback: callback called when the connection is closed.
            host (string): the host name to connect to.
            port (int): the port to connect to.
            unix_domain_socket (string): path to a unix socket to connect to
                (if set, overrides host/port parameters).
            read_page_size (int): page size for reading.
            write_page_size (int): page size for writing.
            connect_timeout (int): timeout (in seconds) for connecting.
            tcp_nodelay (boolean): set TCP_NODELAY on socket.
            aggressive_write (boolean): try to minimize write latency over
                global throughput (default False).
            ioloop (IOLoop): the tornado ioloop to use.
        """
        self.host = host
        self.port = port
        self.unix_domain_socket = unix_domain_socket
        self._state = ConnectionState()
        self._ioloop = ioloop or tornado.ioloop.IOLoop.instance()
        cb = tornado.ioloop.PeriodicCallback(self._on_every_second, 1000,
                                             self._ioloop)
        self.__periodic_callback = cb
        self._read_callback = read_callback
        self._close_callback = close_callback
        self.read_page_size = read_page_size
        self.write_page_size = write_page_size
        self.connect_timeout = connect_timeout
        self.tcp_nodelay = tcp_nodelay
        self.aggressive_write = aggressive_write
        self._write_buffer = WriteBuffer()
        self._listened_events = 0

    def _redis_server(self):
        if self.unix_domain_socket:
            return self.unix_domain_socket
        return "%s:%i" % (self.host, self.port)

    def is_connecting(self):
        """Returns True if the object is connecting."""
        return self._state.is_connecting()

    def is_connected(self):
        """Returns True if the object is connected."""
        return self._state.is_connected()

    @tornado.gen.coroutine
    def connect(self):
        """Connects the object to the host:port.

        Returns:
            Future: a Future object with True as result if the connection
                process was ok.
        """
        if self.is_connected() or self.is_connecting():
            raise tornado.gen.Return(True)
        if self.unix_domain_socket is None:
            self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if self.tcp_nodelay:
                self.__socket.setsockopt(socket.IPPROTO_TCP,
                                         socket.TCP_NODELAY, 1)
        else:
            if not os.path.exists(self.unix_domain_socket):
                LOG.warning("can't connect to %s, file does not exist",
                            self.unix_domain_socket)
                raise tornado.gen.Return(False)
            self.__socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.__socket.setblocking(0)
        self.__periodic_callback.start()
        try:
            LOG.debug("connecting to %s...", self._redis_server())
            self._state.set_connecting()
            if self.unix_domain_socket is None:
                self.__socket.connect((self.host, self.port))
            else:
                self.__socket.connect(self.unix_domain_socket)
        except socket.error as e:
            if (errno_from_exception(e) not in _ERRNO_INPROGRESS and
                    errno_from_exception(e) not in _ERRNO_WOULDBLOCK):
                self.disconnect()
                LOG.warning("can't connect to %s", self._redis_server())
                raise tornado.gen.Return(False)
            self.__socket_fileno = self.__socket.fileno()
            self._register_or_update_event_handler()
            yield self._state.get_changed_state_future()
            if not self.is_connected():
                LOG.warning("can't connect to %s", self._redis_server())
                raise tornado.gen.Return(False)
        else:
            LOG.debug("connected to %s", self._redis_server())
            self.__socket_fileno = self.__socket.fileno()
            self._state.set_connected()
            self._register_or_update_event_handler()
        raise tornado.gen.Return(True)

    def _on_every_second(self):
        if self.is_connecting():
            dt = self._state.get_last_state_change_timedelta()
            if dt.total_seconds() > self.connect_timeout:
                self.disconnect()

    def _register_or_update_event_handler(self, write=True):
        if write:
            listened_events = READ_EVENT | WRITE_EVENT | ERROR_EVENT
        else:
            listened_events = READ_EVENT | ERROR_EVENT
        if self._listened_events == 0:
            try:
                self._ioloop.add_handler(self.__socket_fileno,
                                         self._handle_events, listened_events)
            except (OSError, IOError, ValueError):
                self.disconnect()
                return
        else:
            if self._listened_events != listened_events:
                try:
                    self._ioloop.update_handler(self.__socket_fileno,
                                                listened_events)
                except (OSError, IOError, ValueError):
                    self.disconnect()
                    return
        self._listened_events = listened_events

    def disconnect(self):
        """Disconnects the object.

        Safe method (no exception, even if it's already disconnected or if
        there are some connection errors).
        """
        if not self.is_connected() and not self.is_connecting():
            return
        LOG.debug("disconnecting from %s...", self._redis_server())
        self.__periodic_callback.stop()
        try:
            self._ioloop.remove_handler(self.__socket_fileno)
            self._listened_events = 0
        except:
            pass
        self.__socket_fileno = -1
        try:
            self.__socket.close()
        except:
            pass
        self._state.set_disconnected()
        self._close_callback()
        LOG.debug("disconnected from %s", self._redis_server())

    def _handle_events(self, fd, event):
        if self.is_connecting():
            err = self.__socket.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
            if err != 0:
                LOG.debug("connecting error in _handle_events")
                self.disconnect()
                return
            self._state.set_connected()
            LOG.debug("connected to %s", self._redis_server())
        if not self.is_connected():
            return
        if event & self._ioloop.READ:
            self._handle_read()
        if not self.is_connected():
            return
        if event & self._ioloop.WRITE:
            self._handle_write()
        if not self.is_connected():
            return
        if event & self._ioloop.ERROR:
            LOG.debug("unknown socket error")
            self.disconnect()

    def _handle_read(self):
        chunk = self._read(self.read_page_size)
        if chunk is not None:
            self._read_callback(chunk)

    def _handle_write(self):
        while not self._write_buffer.is_empty():
            ps = self.write_page_size
            data = self._write_buffer.pop_chunk(ps)
            if len(data) > 0:
                try:
                    size = self.__socket.send(data)
                except (socket.error, IOError, OSError) as e:
                    if e.args[0] in _ERRNO_WOULDBLOCK:
                        LOG.debug("write would block")
                        self._write_buffer.appendleft(data)
                        break
                    else:
                        self.disconnect()
                        return
                else:
                    LOG.debug("%i bytes written to the socket", size)
                    if size < len(data):
                        self._write_buffer.appendleft(data[size:])
                        break
        if self._write_buffer.is_empty():
            self._register_or_update_event_handler(write=False)

    def _read(self, size):
        try:
            chunk = self.__socket.recv(size)
            chunk_length = len(chunk)
            if chunk_length > 0:
                LOG.debug("%i bytes read from socket", chunk_length)
                return chunk
            else:
                LOG.debug("closed socket => disconnecting")
                self.disconnect()
        except socket.error as e:
            if e.args[0] in _ERRNO_WOULDBLOCK:
                LOG.debug("read would block")
                return None
            else:
                self.disconnect()

    def write(self, data):
        """Buffers some data to be sent to the host:port in a non blocking way.

        So the data is always buffered and not sent on the socket in a
        synchronous way.

        You can give a WriteBuffer as parameter. The internal Connection
        WriteBuffer will be extended with this one (without copying).

        Args:
            data (str or WriteBuffer): string (or WriteBuffer) to write to
                the host:port.
        """
        if isinstance(data, WriteBuffer):
            self._write_buffer.append(data)
        else:
            if len(data) > 0:
                self._write_buffer.append(data)
        if self.aggressive_write:
            self._handle_write()
        if self._write_buffer._total_length > 0:
            self._register_or_update_event_handler(write=True)
