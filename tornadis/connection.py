#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of tornadis library released under the MIT license.
# See the LICENSE file for more information.

import socket
import tornado.iostream
import tornado.gen
from tornado.util import errno_from_exception
from tornadis.write_buffer import WriteBuffer
from tornadis.exceptions import ConnectionError, ClientError
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
        read_page_size (int): page size for reading.
        write_page_size (int): page size for writing.
        connect_timeout (int): timeout (in seconds) for connecting.
    """

    def __init__(self, read_callback, close_callback,
                 host=tornadis.DEFAULT_HOST,
                 port=tornadis.DEFAULT_PORT,
                 read_page_size=tornadis.DEFAULT_READ_PAGE_SIZE,
                 write_page_size=tornadis.DEFAULT_WRITE_PAGE_SIZE,
                 connect_timeout=tornadis.DEFAULT_CONNECT_TIMEOUT,
                 ioloop=None):
        """Constructor.

        Args:
            read_callback: callback called when there is something to read.
            close_callback: callback called when the connection is closed.
            host (string): the host name to connect to.
            port (int): the port to connect to.
            read_page_size (int): page size for reading.
            write_page_size (int): page size for writing.
            connect_timeout (int): timeout (in seconds) for connecting.
            ioloop (IOLoop): the tornado ioloop to use.
        """
        self.host = host
        self.port = port
        self._state = ConnectionState()
        self.__ioloop = ioloop or tornado.ioloop.IOLoop.instance()
        cb = tornado.ioloop.PeriodicCallback(self._on_every_second, 1000,
                                             self.__ioloop)
        self.__periodic_callback = cb
        self._read_callback = read_callback
        self._close_callback = close_callback
        self.read_page_size = read_page_size
        self.write_page_size = write_page_size
        self.connect_timeout = connect_timeout
        self._write_buffer = WriteBuffer()
        self._listened_events = 0

    def is_connecting(self):
        """Returns True if the object is connecting."""
        return self._state.is_connecting()

    def is_connected(self):
        """Returns True if the object is connected."""
        return self._state.is_connected()

    def _ensure_connected(self):
        if self.is_connected() is False:
            raise ClientError("you are not connected")

    def _ensure_not_connected(self):
        if self.is_connected() is True:
            raise ClientError("you are already connected")

    @tornado.gen.coroutine
    def connect(self):
        """Connects the object to the host:port.

        Returns:
            Future: a Future object with no specific result.

        Raises:
            ConnectionError: when there is a connection error.
        """
        self._ensure_not_connected()
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__socket.setblocking(0)
        self.__periodic_callback.start()
        try:
            LOG.debug("connecting to %s:%i...", self.host, self.port)
            self._state.set_connecting()
            self.__socket.connect((self.host, self.port))
        except socket.error as e:
            if (errno_from_exception(e) not in _ERRNO_INPROGRESS and
                    errno_from_exception(e) not in _ERRNO_WOULDBLOCK):
                self.disconnect()
                raise ConnectionError(e)
            self.__socket_fileno = self.__socket.fileno()
            self._register_or_update_event_handler()
            yield self._state.get_changed_state_future()
            if not self.is_connected():
                raise ConnectionError("connection timeout")
        else:
            LOG.debug("connected to %s:%i", self.host, self.port)
            self.__socket_fileno = self.__socket.fileno()
            self._state.set_connected()
            self._register_or_update_event_handler()

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
                self.__ioloop.add_handler(self.__socket_fileno,
                                          self._handle_events,
                                          listened_events)
            except (OSError, IOError):
                self.disconnect()
                return
        else:
            if self._listened_events != listened_events:
                try:
                    self.__ioloop.update_handler(self.__socket_fileno,
                                                 listened_events)
                except (OSError, IOError):
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
        LOG.debug("disconnecting from %s:%i...", self.host, self.port)
        self.__periodic_callback.stop()
        try:
            self.__ioloop.remove_handler(self.__socket_fileno)
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
        LOG.debug("disconnected from %s:%i", self.host, self.port)

    def _handle_events(self, fd, event):
        if self.is_connecting():
            err = self.__socket.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
            if err != 0:
                LOG.debug("connecting error in _handle_events")
                self.disconnect()
                raise ConnectionError("Connect error: %s" %
                                      errno.errorcode[err])
            self._state.set_connected()
            LOG.debug("connected to %s:%i", self.host, self.port)
        if not self.is_connected():
            return
        if event & self.__ioloop.READ:
            self._handle_read()
        if not self.is_connected():
            return
        if event & self.__ioloop.WRITE:
            self._handle_write()
        if not self.is_connected():
            return
        if event & self.__ioloop.ERROR:
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
                        raise ConnectionError("can't write to socket: %s" % e)
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
                raise ConnectionError("error during socket.recv: %s" % e)

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
        self._ensure_connected()
        if isinstance(data, WriteBuffer):
            self._write_buffer.append(data)
        else:
            if len(data) > 0:
                self._write_buffer.append(data)
        if self._write_buffer._total_length > 0:
            self._register_or_update_event_handler(write=True)
