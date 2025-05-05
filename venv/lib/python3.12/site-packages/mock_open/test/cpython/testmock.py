# This file was adapted from CPython's `Lib/unittest/test/testmock/testmock.py` which is licensed
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

import sys
import tempfile
import unittest
from mock_open import MockOpen as mock_open

try:
    # pylint: disable=no-name-in-module
    from unittest.mock import MagicMock, patch
except ImportError:
    from mock import MagicMock, patch

# bpo-35330 was merged backported from Python v3.8.0 to v3.7.2 and v3.6.8.
# Prior to that, side effects and wrapped objects didn't play nicely.
HAS_BPO_35330 = (3, 7, 2) <= sys.version_info or (3, 6, 8) <= sys.version_info < (3, 7, 0)


class MockTest(unittest.TestCase):
    def test_reset_mock_on_mock_open_issue_18622(self):
        a = mock_open()
        a.reset_mock()

    def test_mock_open_reuse_issue_21750(self):
        mocked_open = mock_open(read_data='data')
        f1 = mocked_open('a-name')
        f1_data = f1.read()
        f2 = mocked_open('another-name')
        f2_data = f2.read()
        self.assertEqual(f1_data, f2_data)

    def test_mock_open_dunder_iter_issue(self):
        # Test dunder_iter method generates the expected result and
        # consumes the iterator.
        mocked_open = mock_open(read_data='Remarkable\nNorwegian Blue')
        f1 = mocked_open('a-name')
        lines = [line for line in f1]
        self.assertEqual(lines[0], 'Remarkable\n')
        self.assertEqual(lines[1], 'Norwegian Blue')
        self.assertEqual(list(f1), [])

    def test_mock_open_using_next(self):
        mocked_open = mock_open(read_data='1st line\n2nd line\n3rd line')
        f1 = mocked_open('a-name')
        line1 = next(f1)
        line2 = f1.__next__()
        lines = [line for line in f1]
        self.assertEqual(line1, '1st line\n')
        self.assertEqual(line2, '2nd line\n')
        self.assertEqual(lines[0], '3rd line')
        self.assertEqual(list(f1), [])
        with self.assertRaises(StopIteration):
            next(f1)

    def test_mock_open_next_with_readline_with_return_value(self):
        mopen = mock_open(read_data='foo\nbarn')
        mopen.return_value.readline.return_value = 'abc'
        self.assertEqual('abc', next(mopen('/some/file')))

    @unittest.skip('mock-open: Covered by other tests')
    def test_mock_open_write(self):
        # Test exception in file writing write()
        mock_namedtemp = mock_open(MagicMock(name='JLV'))
        with patch('tempfile.NamedTemporaryFile', mock_namedtemp):
            mock_filehandle = mock_namedtemp.return_value
            mock_write = mock_filehandle.write
            mock_write.side_effect = OSError('Test 2 Error')
            def attempt():
                tempfile.NamedTemporaryFile().write('asd')
            self.assertRaises(OSError, attempt)

    @unittest.skipUnless(HAS_BPO_35330, 'mock-open: Requires bpo-35330')
    def test_mock_open_alter_readline(self):
        mopen = mock_open(read_data='foo\nbarn')
        mopen.return_value.readline.side_effect = lambda *args:'abc'
        first = mopen('/some/file').readline()
        second = mopen('/some/file').readline()
        self.assertEqual('abc', first)
        self.assertEqual('abc', second)

    def test_mock_open_after_eof(self):
        # read, readline and readlines should work after end of file.
        _open = mock_open(read_data='foo')
        h = _open('bar')
        h.read()
        self.assertEqual('', h.read())
        self.assertEqual('', h.read())
        self.assertEqual('', h.readline())
        self.assertEqual('', h.readline())
        self.assertEqual([], h.readlines())
        self.assertEqual([], h.readlines())
