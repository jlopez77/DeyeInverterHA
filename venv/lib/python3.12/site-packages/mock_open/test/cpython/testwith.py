# This file was adapted from CPython's `Lib/unittest/test/testmock/testwith.py` which is licensed
# under the PSF license agreement.
#
# In accordance with the license, these are the major changes made to file:
#  * Any tests or code not directly used to test `unittest.mock.mock_open` was deleted.
#  * Instead of using `unittest.mock.mock_open`, the mock-open library's `MockOpen` was imported
#    instead as `mock_open` to keep changes to the test code minimal.
#  * Where there were functional differences between `unittest.mock.mock_open` and `MockOpen` the
#    tests were modified to accomodate the latter rather than the former. These were mostly around
#    `MockOpen`'s constructor requiring a "path" argument and `FileLikeMock`'s  `__exit__` calling
#    `close` on the underlying file-like object.
#
# Copyright © 2001-2020 Python Software Foundation; All Rights Reserved.

import unittest
from mock_open import MockOpen as mock_open

try:
    # pylint: disable=no-name-in-module
    from unittest.mock import MagicMock, patch, call
except ImportError:
    from mock import MagicMock, patch, call


class TestMockOpen(unittest.TestCase):
    def test_mock_open(self):
        mock = mock_open()
        with patch('%s.open' % __name__, mock, create=True) as patched:
            self.assertIs(patched, mock)
            open('foo')

        mock.assert_called_once_with('foo')

    def test_mock_open_context_manager(self):
        mock = mock_open()
        handle = mock.return_value
        with patch('%s.open' % __name__, mock, create=True):
            with open('foo') as f:
                f.read()

        expected_calls = [call('foo'), call().__enter__(), call().read(),
                          call().__exit__(None, None, None), call().close()]
        self.assertEqual(mock.mock_calls, expected_calls)
        self.assertIs(f, handle)

    def test_mock_open_context_manager_multiple_times(self):
        mock = mock_open()
        with patch('%s.open' % __name__, mock, create=True):
            with open('foo') as f:
                f.read()
            with open('bar') as f:
                f.read()

        expected_calls = [
            call('foo'), call().__enter__(), call().read(),
            call().__exit__(None, None, None), call().close(),
            call('bar'), call().__enter__(), call().read(),
            call().__exit__(None, None, None), call().close()]
        self.assertEqual(mock.mock_calls, expected_calls)

    def test_explicit_mock(self):
        mock = MagicMock()
        mock_open(mock)

        with patch('%s.open' % __name__, mock, create=True) as patched:
            self.assertIs(patched, mock)
            open('foo')

        mock.assert_called_once_with('foo')

    def test_read_data(self):
        mock = mock_open(read_data='foo')
        with patch('%s.open' % __name__, mock, create=True):
            h = open('bar')
            result = h.read()

        self.assertEqual(result, 'foo')

    def test_readline_data(self):
        # Check that readline will return all the lines from the fake file
        # And that once fully consumed, readline will return an empty string.
        mock = mock_open(read_data='foo\nbar\nbaz\n')
        with patch('%s.open' % __name__, mock, create=True):
            h = open('bar')
            line1 = h.readline()
            line2 = h.readline()
            line3 = h.readline()
        self.assertEqual(line1, 'foo\n')
        self.assertEqual(line2, 'bar\n')
        self.assertEqual(line3, 'baz\n')
        self.assertEqual(h.readline(), '')

        # Check that we properly emulate a file that doesn't end in a newline
        mock = mock_open(read_data='foo')
        with patch('%s.open' % __name__, mock, create=True):
            h = open('bar')
            result = h.readline()
        self.assertEqual(result, 'foo')
        self.assertEqual(h.readline(), '')

    def test_dunder_iter_data(self):
        # Check that dunder_iter will return all the lines from the fake file.
        mock = mock_open(read_data='foo\nbar\nbaz\n')
        with patch('%s.open' % __name__, mock, create=True):
            h = open('bar')
            lines = [l for l in h]
        self.assertEqual(lines[0], 'foo\n')
        self.assertEqual(lines[1], 'bar\n')
        self.assertEqual(lines[2], 'baz\n')
        self.assertEqual(h.readline(), '')
        with self.assertRaises(StopIteration):
            next(h)

    def test_next_data(self):
        # Check that next will correctly return the next available
        # line and plays well with the dunder_iter part.
        mock = mock_open(read_data='foo\nbar\nbaz\n')
        with patch('%s.open' % __name__, mock, create=True):
            h = open('bar')
            line1 = next(h)
            line2 = next(h)
            lines = [l for l in h]
        self.assertEqual(line1, 'foo\n')
        self.assertEqual(line2, 'bar\n')
        self.assertEqual(lines[0], 'baz\n')
        self.assertEqual(h.readline(), '')

    def test_readlines_data(self):
        # Test that emulating a file that ends in a newline character works
        mock = mock_open(read_data='foo\nbar\nbaz\n')
        with patch('%s.open' % __name__, mock, create=True):
            h = open('bar')
            result = h.readlines()
        self.assertEqual(result, ['foo\n', 'bar\n', 'baz\n'])

        # Test that files without a final newline will also be correctly
        # emulated
        mock = mock_open(read_data='foo\nbar\nbaz')
        with patch('%s.open' % __name__, mock, create=True):
            h = open('bar')
            result = h.readlines()

        self.assertEqual(result, ['foo\n', 'bar\n', 'baz'])

    def test_read_bytes(self):
        mock = mock_open(read_data=b'\xc6')
        with patch('%s.open' % __name__, mock, create=True):
            with open('abc', 'rb') as f:
                result = f.read()
        self.assertEqual(result, b'\xc6')

    def test_readline_bytes(self):
        m = mock_open(read_data=b'abc\ndef\nghi\n')
        with patch('%s.open' % __name__, m, create=True):
            with open('abc', 'rb') as f:
                line1 = f.readline()
                line2 = f.readline()
                line3 = f.readline()
        self.assertEqual(line1, b'abc\n')
        self.assertEqual(line2, b'def\n')
        self.assertEqual(line3, b'ghi\n')

    def test_readlines_bytes(self):
        m = mock_open(read_data=b'abc\ndef\nghi\n')
        with patch('%s.open' % __name__, m, create=True):
            with open('abc', 'rb') as f:
                result = f.readlines()
        self.assertEqual(result, [b'abc\n', b'def\n', b'ghi\n'])

    def test_mock_open_read_with_argument(self):
        # At one point calling read with an argument was broken
        # for mocks returned by mock_open
        some_data = 'foo\nbar\nbaz'
        mock = mock_open(read_data=some_data)
        self.assertEqual(mock('/some/file').read(10), some_data[:10])
        self.assertEqual(mock('/some/file').read(10), some_data[:10])

        f = mock('/some/file')
        self.assertEqual(f.read(10), some_data[:10])
        self.assertEqual(f.read(10), some_data[10:])

    def test_interleaved_reads(self):
        # Test that calling read, readline, and readlines pulls data
        # sequentially from the data we preload with
        mock = mock_open(read_data='foo\nbar\nbaz\n')
        with patch('%s.open' % __name__, mock, create=True):
            h = open('bar')
            line1 = h.readline()
            rest = h.readlines()
        self.assertEqual(line1, 'foo\n')
        self.assertEqual(rest, ['bar\n', 'baz\n'])

        mock = mock_open(read_data='foo\nbar\nbaz\n')
        with patch('%s.open' % __name__, mock, create=True):
            h = open('bar')
            line1 = h.readline()
            rest = h.read()
        self.assertEqual(line1, 'foo\n')
        self.assertEqual(rest, 'bar\nbaz\n')

    def test_overriding_return_values(self):
        mock = mock_open(read_data='foo')
        handle = mock('/some/file')

        handle.read.return_value = 'bar'
        handle.readline.return_value = 'bar'
        handle.readlines.return_value = ['bar']

        self.assertEqual(handle.read(), 'bar')
        self.assertEqual(handle.readline(), 'bar')
        self.assertEqual(handle.readlines(), ['bar'])

        # call repeatedly to check that a StopIteration is not propagated
        self.assertEqual(handle.readline(), 'bar')
        self.assertEqual(handle.readline(), 'bar')
