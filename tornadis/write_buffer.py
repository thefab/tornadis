#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of tornadis library released under the MIT license.
# See the LICENSE file for more information.

import collections


class WriteBuffer(object):
    """Write buffer implementation optimized for reading by max sized chunks.

    It is built on a deque and memoryviews to avoid too much string copies.

    Attributes:
        use_memory_view_min_size (int): minimum size before using memoryview
            objects (to avoid object creation overhead bigger than string
            copy for this size)
        _deque (collections.deque): deque object to store each write
            (without copy)
        _has_view (boolean): True if there is some memoryview objects inside
            the deque (if _has_view=False, there are some
            "fastpath optimizations")
        _total_length (int): total size (in bytes) of the buffer content
    """

    def __init__(self, use_memory_view_min_size=4096):
        """Constructor.

        Args:
            use_memory_view_min_size (int): minimum size before using
                memoryview objects (advanced option, the default is probably
                good for you).
        """
        self.use_memory_view_min_size = use_memory_view_min_size
        self._deque = collections.deque()
        self.clear()

    def clear(self):
        """Resets the object at its initial (empty) state."""
        self._deque.clear()
        self._total_length = 0
        self._has_view = False

    def __str__(self):
        return self._tobytes()

    def __bytes__(self):
        return self._tobytes()

    def __len__(self):
        return self._total_length

    def _tobytes(self):
        """Serializes the write buffer into a single string (bytes).

        Returns:
            a string (bytes) object.
        """
        if not self._has_view:
            # fast path optimization
            if len(self._deque) == 0:
                return b""
            elif len(self._deque) == 1:
                # no copy
                return self._deque[0]
            else:
                return b"".join(self._deque)
        else:
            tmp = [x.tobytes() if isinstance(x, memoryview) else x
                   for x in self._deque]
            return b"".join(tmp)

    def is_empty(self):
        """Returns True if the buffer is empty.

        Returns:
            True or False.
        """
        return self._total_length == 0

    def append(self, data):
        """Appends some data to end of the buffer (right).

        No string copy is done during this operation.

        Args:
            data: data to put in the buffer (can be string, memoryview or
                another WriteBuffer).
        """
        self._append(data, True)

    def appendleft(self, data):
        """Appends some data at the beginning of the buffer (left).

        No string copy is done during this operation.

        Args:
            data: data to put in the buffer (can be string, memoryview or
                another WriteBuffer).
        """
        self._append(data, False)

    def _append(self, data, right):
        if isinstance(data, WriteBuffer):
            # data is another writebuffer
            if right:
                self._deque.extend(data._deque)
            else:
                self._deque.extendleft(data._deque)
            self._total_length += data._total_length
            self._has_view = self._has_view and data._has_view
        else:
            length = len(data)
            if length == 0:
                return
            if isinstance(data, memoryview):
                # data is a memory viewobject
                # nothing spacial but now the buffer has views
                self._has_view = True
            self._total_length += length
            if right:
                self._deque.append(data)
            else:
                self._deque.appendleft(data)

    def _get_pointer_or_memoryview(self, data, data_length):
        if data_length < self.use_memory_view_min_size \
           or isinstance(data, memoryview):
            return data
        else:
            return memoryview(data)

    def pop_chunk(self, chunk_max_size):
        """Pops a chunk of the given max size.

        Optimized to avoid too much string copies.

        Args:
            chunk_max_size (int): max size of the returned chunk.

        Returns:
            string (bytes) with a size <= chunk_max_size.
        """
        if self._total_length < chunk_max_size:
            # fastpath (the whole queue fit in a single chunk)
            res = self._tobytes()
            self.clear()
            return res
        first_iteration = True
        while True:
            try:
                data = self._deque.popleft()
                data_length = len(data)
                self._total_length -= data_length
                if first_iteration:
                    # first iteration
                    if data_length == chunk_max_size:
                        # we are lucky !
                        return data
                    elif data_length > chunk_max_size:
                        # we have enough data at first iteration
                        # => fast path optimization
                        view = self._get_pointer_or_memoryview(data,
                                                               data_length)
                        self.appendleft(view[chunk_max_size:])
                        return view[:chunk_max_size]
                    else:
                        # no single iteration fast path optimization :-(
                        # let's use a WriteBuffer to build the result chunk
                        chunk_write_buffer = WriteBuffer()
                else:
                    # not first iteration
                    if chunk_write_buffer._total_length + data_length \
                       > chunk_max_size:
                        view = self._get_pointer_or_memoryview(data,
                                                               data_length)
                        limit = chunk_max_size - \
                            chunk_write_buffer._total_length - data_length
                        self.appendleft(view[limit:])
                        data = view[:limit]
                chunk_write_buffer.append(data)
                if chunk_write_buffer._total_length >= chunk_max_size:
                    break
            except IndexError:
                # the buffer is empty (so no memoryview inside)
                self._has_view = False
                break
            first_iteration = False
        return chunk_write_buffer._tobytes()
