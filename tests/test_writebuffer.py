#!/usr/bin/env python
# -*- coding: utf-8 -*-

from unittest import TestCase
from tornadis.write_buffer import WriteBuffer


class WriteBufferTestCase(TestCase):

    def _make_test_buffer(self):
        x = WriteBuffer()
        x.append(b"23")
        x.append(b"4")
        x.append(b"")
        x.append(b"56789")
        x.appendleft(b"1")
        return x

    def _pop_chunk_as_str(self, buf, max_size):
        tmp = buf.pop_chunk(max_size)
        if isinstance(tmp, memoryview):
            return tmp.tobytes()
        else:
            return tmp

    def test_empty_write_buffer(self):
        x = WriteBuffer()
        s = bytes(x)
        self.assertEqual(s, b"")
        c = x.pop_chunk(4096)
        self.assertEqual(c, b"")
        self.assertEqual(len(x), 0)

    def test_write_buffer1(self):
        b = self._make_test_buffer()
        s = bytes(b)
        self.assertEqual(len(b), 9)
        self.assertEqual(s, b"123456789")
        self.assertFalse(b.is_empty())
        self.assertEqual(b._total_length, 9)
        b2 = self._make_test_buffer()
        b.append(b2)
        s = bytes(b)
        self.assertEqual(s, b"123456789123456789")
        self.assertFalse(b.is_empty())
        self.assertEqual(b._total_length, 18)
        chunk = self._pop_chunk_as_str(b, 1000)
        self.assertEqual(chunk, b"123456789123456789")
        self.assertTrue(b.is_empty())

    def test_write_buffer2(self):
        b = self._make_test_buffer()
        chunk = self._pop_chunk_as_str(b, 1)
        self.assertEqual(chunk, b"1")
        self.assertEqual(bytes(b), b"23456789")
        self.assertEqual(b._total_length, 8)
        chunk = self._pop_chunk_as_str(b, 1)
        self.assertEqual(chunk, b"2")
        self.assertEqual(bytes(b), b"3456789")
        self.assertEqual(b._total_length, 7)
        chunk = self._pop_chunk_as_str(b, 4)
        self.assertEqual(chunk, b"3456")
        self.assertEqual(bytes(b), b"789")
        self.assertEqual(b._total_length, 3)
        chunk = self._pop_chunk_as_str(b, 10)
        self.assertEqual(chunk, b"789")
        self.assertEqual(bytes(b), b"")
        self.assertEqual(b._total_length, 0)

    def test_write_buffer3(self):
        b = WriteBuffer()
        b.append(b"x" * 10000)
        chunk = self._pop_chunk_as_str(b, 4000)
        self.assertEqual(len(chunk), 4000)
        chunk = self._pop_chunk_as_str(b, 4000)
        self.assertEqual(len(chunk), 4000)
        chunk = self._pop_chunk_as_str(b, 4000)
        self.assertEqual(len(chunk), 2000)
