"""Test cases for the mocks module."""

import sys
import unittest
from functools import wraps
from mock_open.mocks import MockOpen, FileLikeMock

try:
    # pylint: disable=no-name-in-module
    from unittest.mock import patch, call, NonCallableMock, DEFAULT
except ImportError:
    from mock import patch, call, NonCallableMock, DEFAULT

if sys.version_info < (3, 0):
    OPEN = '__builtin__.open'
else:
    OPEN = 'builtins.open'


@patch(OPEN, new_callable=MockOpen)
class TestOpenSingleFiles(unittest.TestCase):
    """Test the MockOpen and FileLikeMock classes for single file usage."""
    def test_read(self, mock_open):
        """Check effects of reading from an empty file."""
        handle = open('/path/to/file', 'r')
        self.assertFalse(handle.closed)
        self.assertEqual('/path/to/file', handle.name)
        self.assertEqual('r', handle.mode)
        self.assertEqual(0, handle.tell())

        text = handle.read()
        self.assertEqual(0, handle.tell())
        self.assertEqual('', text)

        handle.close()
        self.assertTrue(handle.closed)

        self.assertEqual(handle, mock_open.return_value)
        mock_open.assert_called_once_with('/path/to/file', 'r')
        handle.read.assert_called_once_with()
        handle.close.assert_called_once_with()

    def test_write(self, mock_open):
        """Check effects of writing to a file."""
        handle = open('/path/to/file', 'w')
        self.assertFalse(handle.closed)
        self.assertEqual('/path/to/file', handle.name)
        self.assertEqual('w', handle.mode)
        self.assertEqual(0, handle.tell())

        handle.write("some text\n")
        self.assertEqual(len("some text\n"), handle.tell())
        handle.write('More text!')
        self.assertEqual(
            len('some text\n') + len('More text!'),
            handle.tell())

        handle.close()
        self.assertTrue(handle.closed)

        self.assertEqual(handle, mock_open.return_value)
        mock_open.assert_called_once_with('/path/to/file', 'w')
        self.assertEqual(
            [call('some text\n'), call('More text!'), ],
            handle.write.mock_calls)
        self.assertEqual('some text\nMore text!', handle.read_data)
        handle.close.assert_called_once_with()

    def test_context_manager(self, mock_open):
        """Check calls made when `open` is used as a context manager."""
        with open('/path/to/file', 'r') as handle:
            self.assertFalse(handle.closed)
            self.assertEqual('/path/to/file', handle.name)
            self.assertEqual('r', handle.mode)
            self.assertEqual(0, handle.tell())

        mock_open.assert_has_calls([
            call('/path/to/file', 'r'),
            call().__enter__(),
            call().tell(),
            call().__exit__(None, None, None),
            call().close(),
        ])

    def test_read_as_context_manager(self, mock_open):
        """Check effects of reading from an empty file using a context
        manager.
        """
        with open('/path/to/file', 'r') as handle:
            text = handle.read()
            self.assertEqual(0, handle.tell())
            self.assertEqual('', text)

        self.assertTrue(handle.closed)
        self.assertEqual(handle, mock_open.return_value)
        mock_open.assert_called_once_with('/path/to/file', 'r')
        handle.read.assert_called_once_with()
        handle.close.assert_called_once_with()

    def test_write_as_context_manager(self, mock_open):
        """Check effects of writing to a file using a context manager."""
        with open('/path/to/file', 'w') as handle:
            handle.write("some text\n")
            self.assertEqual(len("some text\n"), handle.tell())
            handle.write('More text!')
            self.assertEqual(
                len('some text\n') + len('More text!'),
                handle.tell())

        self.assertTrue(handle.closed)
        self.assertEqual(handle, mock_open.return_value)
        mock_open.assert_called_once_with('/path/to/file', 'w')
        self.assertEqual(
            [call('some text\n'), call('More text!'), ],
            handle.write.mock_calls)
        self.assertEqual('some text\nMore text!', handle.read_data)
        handle.close.assert_called_once_with()

    def test_seek(self, _):
        """Check calling seek()."""
        with open('/path/to/file', 'w+') as handle:
            handle.write('There\'s no place like home')
            handle.seek(len('There\'s '))
            self.assertEqual('no place like home', handle.read())

    def test_set_contents(self, mock_open):
        """Check setting file's contents before reading from it."""
        contents = [
            'This is the first line',
            'This is the second',
            'This is the third line',
        ]

        # We even allow adding contents to the file incrementally.
        mock_open.return_value.read_data = '\n'.join(contents[:-1])
        mock_open.return_value.read_data += '\n' + contents[-1]

        with open('/path/to/file', 'r') as handle:
            data = handle.read()

        handle.read.assert_called_once_with()
        self.assertEqual('\n'.join(contents), data)

    def test_read_size(self, mock_open):
        """Check reading a certain amount of bytes from the file."""
        mock_open.return_value.read_data = '0123456789'
        with open('/path/to/file', 'r') as handle:
            self.assertEqual('0123', handle.read(4))
            self.assertEqual('4567', handle.read(4))
            self.assertEqual('89', handle.read())

    def test_different_read_calls(self, mock_open):
        """Check that read/readline/readlines all work in sync."""
        contents = [
            'Now that she\'s back in the atmosphere',
            'With drops of Jupiter in her hair, hey, hey, hey',
            'She acts like summer and walks like rain',
            'Reminds me that there\'s a time to change, hey, hey, hey',
            'Since the return from her stay on the moon',
            'She listens like spring and she talks like June, hey, hey, hey',
        ]

        mock_open.return_value.read_data = '\n'.join(contents)
        with open('/path/to/file', 'r') as handle:
            first_line = handle.read(len(contents[0]) + 1)
            second_line = handle.readline()
            third_line = handle.read(len(contents[2]) + 1)
            rest = handle.readlines()

            self.assertEqual(contents[0] + '\n', first_line)
            self.assertEqual(contents[1] + '\n', second_line)
            self.assertEqual(contents[2] + '\n', third_line)
            self.assertEqual('\n'.join(contents[3:]), ''.join(rest))

    def test_different_write_calls(self, _):
        """Check multiple calls to write and writelines."""
        contents = [
            'They paved paradise',
            'And put up a parking lot',
            'With a pink hotel, a boutique',
            'And a swinging hot SPOT',
            'Don\'t it always seem to go',
            'That you don\'t know what you\'ve got',
            '\'Til it\'s gone',
            'They paved paradise',
            'And put up a parking lot',
        ]

        with open('/path/to/file', 'w') as handle:
            handle.write(contents[0] + '\n')
            handle.write(contents[1] + '\n')
            handle.writelines(line + '\n' for line in contents[2:4])
            handle.write(contents[4] + '\n')
            handle.writelines(line + '\n' for line in contents[5:])

        self.assertEqual(contents, handle.read_data.splitlines())

    def test_iteration(self, mock_open):
        """Test iterating over the file handle."""
        contents = [
            "So bye, bye, Miss American Pie\n",
            "Drove my Chevy to the levee but the levee was dry\n",
            "And them good ole boys were drinking whiskey 'n rye\n",
            "Singin' this'll be the day that I die\n",
            'This\'ll be the day that I die',
        ]

        mock_open.return_value.read_data = ''.join(contents)
        with open('/path/to/file') as handle:
            for (i, line) in enumerate(handle):
                self.assertEqual(contents[i], line)

        # Same thing but using `next`.
        with open('/path/to/file') as handle:
            for line in contents:
                self.assertEqual(line, next(handle))
            with self.assertRaises(StopIteration):
                next(handle)

    def test_getitem_after_call(self, mock_open):
        """Retrieving a handle after the call to open() should give us the same
        object.
        """
        with open('/path/to/file', 'r') as handle:
            pass

        self.assertEqual(handle, mock_open['/path/to/file'])

    def test_setting_custom_mock(self, mock_open):
        """Check 'manually' setting a mock for a file."""
        custom_mock = NonCallableMock()
        mock_open['/path/to/file'] = custom_mock

        # Make sure other files aren't affected.
        self.assertIsInstance(open('/path/to/other_file', 'r'), FileLikeMock)

        # Check with a regular call.
        self.assertEqual(custom_mock, open('/path/to/file', 'r'))

        # Check as a context manager.
        custom_mock.read.side_effect = IOError()
        custom_mock.write.side_effect = IOError()
        with open('/path/to/file') as handle:
            self.assertIs(custom_mock, handle)
            self.assertRaises(IOError, handle.read)
            self.assertRaises(IOError, handle.write, 'error')


@patch(OPEN, new_callable=MockOpen)
class TestMultipleCalls(unittest.TestCase):
    """Test multiple calls to open()."""
    def test_read_then_write(self, _):
        """Accessing the same file should handle the same object.

        Reading from a file after writing to it should give us the same
        contents.
        """
        with open('/path/to/file', 'w') as first_handle:
            first_handle.write('Ground control to Major Tom')
            self.assertEqual('w', first_handle.mode)

        with open('/path/to/file', 'r') as second_handle:
            contents = second_handle.read()
            self.assertEqual('r', second_handle.mode)

        self.assertEqual(first_handle, second_handle)
        self.assertEqual('Ground control to Major Tom', contents)

    def test_access_different_files(self, mock_open):
        """Check access to different files with multiple calls to open()."""
        first_handle = mock_open['/path/to/first_file']
        second_handle = mock_open['/path/to/second_file']

        # Paths should be set when created, if possible.
        # Note this isn't the case when not specifically instantiating a file
        # mock (eg., by using `return_value` instead).
        self.assertEqual('/path/to/first_file', first_handle.name)
        self.assertEqual('/path/to/second_file', second_handle.name)

        first_handle.read_data = 'This is the FIRST file'
        second_handle.read_data = 'This is the SECOND file'

        with open('/path/to/first_file', 'r') as handle:
            self.assertEqual('/path/to/first_file', handle.name)
            self.assertEqual('This is the FIRST file', handle.read())

        with open('/path/to/second_file', 'r') as handle:
            self.assertEqual('/path/to/second_file', handle.name)
            self.assertEqual('This is the SECOND file', handle.read())

        # return_value is set to the last handle returned.
        self.assertEqual(second_handle, mock_open.return_value)

        self.assertEqual('r', first_handle.mode)
        self.assertEqual('r', second_handle.mode)
        first_handle.read.assert_called_once_with()
        second_handle.read.assert_called_once_with()

    def test_return_value(self, mock_open):
        """Check that `return_value` always returns the last file mock."""
        with open('/path/to/first_file', 'r'):
            pass

        with open('/path/to/second_file', 'r') as handle:
            self.assertEqual(handle, mock_open.return_value)

    def test_multiple_opens(self, mock_open):
        """Verify position when opening file multiple times."""
        mock_open.return_value.read_data = 'SOME DATA'
        with open('/some/file') as first_handle:
            self.assertEqual(0, first_handle.tell())
            self.assertEqual('SOME', first_handle.read(4))
            self.assertEqual(4, first_handle.tell())

        # Open file a second time.
        with open('/some/file') as second_handle:
            self.assertEqual(0, second_handle.tell())

        # Open file a third time to append to it.
        with open('/some/file', 'a') as third_handle:
            self.assertEqual(9, third_handle.tell())

        # Same thing, but not as a context manager.
        # TODO: In this case we differ from `open` implementation since all of these handles
        # are actually the same `FileLikeMock` instance. A better mock would provide multiple
        # instances.
        first_handle = open('/some/file')
        self.assertEqual(0, first_handle.tell())
        self.assertEqual('SOME', first_handle.read(4))
        self.assertEqual(4, first_handle.tell())

        second_handle = open('/some/file')
        self.assertEqual(0, second_handle.tell())
        self.assertNotEqual(4, first_handle.tell()) # FIXME?

        third_handle = open('/some/file', 'a')
        self.assertEqual(9, third_handle.tell())
        self.assertNotEqual(4, first_handle.tell()) # FIXME?
        self.assertNotEqual(0, second_handle.tell()) # FIXME?


@patch(OPEN, new_callable=MockOpen)
class TestSideEffects(unittest.TestCase):
    """Test setting the side_effect attribute in various situations."""
    def test_error_on_open(self, mock_open):
        """Simulate error opening a file."""
        mock_open.side_effect = IOError()

        self.assertRaises(IOError, open, '/not/there', 'r')

    def test_error_on_any_open(self, mock_open):
        """Simulate errors opening any file."""
        mock_open.side_effect = IOError()

        self.assertRaises(IOError, open, '/not/there_1', 'r')
        self.assertRaises(IOError, open, '/not/there_2', 'r')
        self.assertRaises(IOError, open, '/not/there_3', 'r')

    def test_error_on_all_but_one(self, mock_open):
        """Setting a global error but allowing specific file/s."""
        mock_open.side_effect = IOError()
        mock_open['/is/there'].side_effect = None

        self.assertRaises(IOError, open, '/not/there_1', 'r')
        self.assertRaises(IOError, open, '/not/there_2', 'r')

        with open('/is/there', 'r'):
            pass

    def test_error_list(self, mock_open):
        """Setting a global side effect iterator."""
        mock_open.side_effect = [ValueError(), RuntimeError(), DEFAULT, ]

        self.assertRaises(ValueError, open, '/not/there_1', 'r')
        self.assertRaises(RuntimeError, open, '/not/there_2', 'r')

        with open('/is/there', 'r'):
            pass

    def test_error_on_read(self, mock_open):
        """Simulate error when reading from file."""
        mock_open.return_value.read.side_effect = IOError()

        with open('/path/to/file', 'w') as handle:
            with self.assertRaises(IOError):
                handle.read()

    def test_error_on_write(self, mock_open):
        """Simulate error when writing to file."""
        mock_open.return_value.write.side_effect = IOError()

        with open('/path/to/file', 'r') as handle:
            with self.assertRaises(IOError):
                handle.write('text')

    def test_error_by_name(self, mock_open):
        """Raise an exception for a specific path."""
        mock_open['/path/to/error_file'].side_effect = IOError()

        # Trying to open a different file should be OK.
        with open('/path/to/allowed_file', 'r'):
            pass

        # But opening the bad file should raise an exception.
        self.assertRaises(IOError, open, '/path/to/error_file', 'r')

        # Reset open's side effect and check read/write side effects.
        mock_open['/path/to/error_file'].side_effect = None
        mock_open['/path/to/error_file'].read.side_effect = IOError()
        mock_open['/path/to/error_file'].write.side_effect = IOError()
        with open('/path/to/error_file', 'r') as handle:
            self.assertRaises(IOError, handle.read)
            self.assertRaises(IOError, handle.write, 'Bad write')

    def test_read_return_value(self, mock_open):
        """Set the return value from read()."""
        mock_open.return_value.read_data = 'Some text'
        mock_open.return_value.read.return_value = 'New text'

        with open('/path/to/file', 'w') as handle:
            contents = handle.read()

        self.assertEqual('New text', contents)

    def test_read_side_effect(self, mock_open):
        """Add a side effect to read().

        Setting a side_effect can't change the return value.
        """
        def set_sentinal():
            # pylint: disable=missing-docstring
            sentinal[0] = True
            return DEFAULT

        # If we define contents as a 'simple' variable (just None, for example)
        # the assignment inside fake_write() will assign to a local variable
        # instead of the 'outer' contents variable.
        sentinal = [False, ]
        mock_open.return_value.read_data = 'Some text'
        mock_open.return_value.read.side_effect = set_sentinal

        with open('/path/to/file', 'w') as handle:
            contents = handle.read()

        self.assertEqual('Some text', contents)
        self.assertTrue(sentinal[0])

    def test_write_side_effect(self, mock_open):
        """Add a side effect to write()."""
        def set_sentinal(data):
            # pylint: disable=missing-docstring
            sentinal[0] = True
            return DEFAULT

        # Avoid uninitialized assignment (see test_read_side_effect()).
        sentinal = [False, ]
        mock_open.return_value.write.side_effect = set_sentinal

        with open('/path/to/file', 'w') as handle:
            handle.write('Some text')

        self.assertEqual('Some text', handle.read_data)
        self.assertTrue(sentinal[0])

    def test_multiple_files(self, mock_open):
        """Test different side effects for different files."""
        mock_open['fail_on_open'].side_effect = IOError()
        mock_open['fail_on_read'].read.side_effect = IOError()
        mock_open['fail_on_write'].write.side_effect = IOError()

        with open('success', 'w') as handle:
            handle.write('some text')

        self.assertRaises(IOError, open, 'fail_on_open', 'rb')

        with open('fail_on_read', 'r') as handle:
            self.assertRaises(IOError, handle.read)

        with open('fail_on_write', 'w') as handle:
            self.assertRaises(IOError, handle.write, 'not to be written')

        with open('success', 'r') as handle:
            self.assertEqual('some text', handle.read())


class TestAPI(unittest.TestCase):
    """Test conformance to mock library's API."""
    def test_read_data(self):
        """Check passing of `read_data` to the constructor."""
        mock_open = MockOpen(read_data='Data from the file')

        with patch(OPEN, mock_open):
            with open('/path/to/file', 'r') as handle:
                contents = handle.read()

        self.assertEqual('Data from the file', contents)

    def test_reset_mock(self):
        """Check that reset_mock() works."""
        # Reset globally for all file mocks.
        mock_open = MockOpen(read_data='Global')
        mock_open['/path/to/file'].read_data = 'File-specific'
        mock_open.reset_mock()

        with patch(OPEN, mock_open):
            with open('/path/to/file', 'r') as handle:
                self.assertEqual('', handle.read())

        # Reset a for a specific file mock.
        mock_open = MockOpen(read_data='Global')
        mock_open['/path/to/file'].read_data = 'File-specific'
        mock_open['/path/to/file'].reset_mock()

        with patch(OPEN, mock_open):
            with open('/path/to/file', 'r') as handle:
                self.assertEqual('', handle.read())

            with open('/path/to/other/file', 'r') as handle:
                self.assertEqual('Global', handle.read())


class TestModes(unittest.TestCase):
    """Test different modes behavior."""
    @patch(OPEN, new_callable=MockOpen)
    def test_default_mode(self, mock_open):
        """Default mode is 'r'."""
        with open('/path/to/file') as _:
            pass

        mock_open.assert_called_once_with('/path/to/file')
        self.assertEqual('r', mock_open.return_value.mode)

    @patch(OPEN, new_callable=MockOpen)
    def test_open_as_text(self, mock_open):
        """Read/write to file as text (no 'b')."""
        with open('/path/to/empty_file', 'r') as handle:
            contents = handle.read()

        self.assertIsInstance(contents, str)
        self.assertEqual('', contents)

        mock_open['/path/to/file'].read_data = 'Contents'

        with open('/path/to/file', 'r') as handle:
            contents = handle.read()

        self.assertIsInstance(contents, str)
        self.assertEqual('Contents', contents)

        with open('/path/to/file', 'w') as handle:
            handle.write('New contents')

        self.assertEqual('New contents', handle.read_data)

    @patch(OPEN, new_callable=MockOpen)
    def test_open_as_binary(self, mock_open):
        """Read/write to file as binary data (with 'b')."""
        with open('/path/to/empty_file', 'rb') as handle:
            contents = handle.read()

        self.assertIsInstance(contents, bytes)
        self.assertEqual(b'', contents)

        mock_open['/path/to/file'].read_data = b'Contents'

        with open('/path/to/file', 'rb') as handle:
            contents = handle.read()

        self.assertIsInstance(contents, bytes)
        self.assertEqual(b'Contents', contents)

        with open('/path/to/file', 'wb') as handle:
            handle.write(b'New contents')

        self.assertEqual(b'New contents', handle.read_data)

    @patch(OPEN, new_callable=MockOpen)
    def test_different_opens(self, _):
        """Open the same file as text/binary."""
        with open('/path/to/file', 'w') as handle:
            handle.write('Textual content')

        self.assertIsInstance(handle.read_data, str)

        with open('/path/to/file', 'rb') as handle:
            contents = handle.read()

        self.assertIsInstance(contents, bytes)
        self.assertEqual(b'Textual content', contents)

        with open('/path/to/file', 'r') as handle:
            contents = handle.read()

        self.assertIsInstance(contents, str)
        self.assertEqual('Textual content', contents)


class TestIssues(unittest.TestCase):
    """Test cases related to issues on GitHub.

    See https://github.com/nivbend/mock-open
    """
    def test_issue_1(self):
        """Setting a side effect on a specific open() shouldn't affect
        consecutive calls.
        """
        mock_open = MockOpen()
        mock_open['fail_on_open'].side_effect = IOError()

        with patch(OPEN, mock_open):
            with self.assertRaises(IOError):
                open('fail_on_open', 'rb')

            with open('success', 'r') as handle:
                self.assertEqual('', handle.read())

    def test_issue_3(self):
        """Position in file should be set to 0 after the call to `open`."""
        mock_open = MockOpen(read_data='some content')

        with patch(OPEN, mock_open):
            handle = open('/path/to/file', 'r')
            self.assertEqual(0, handle.tell())
            self.assertEqual('some content', handle.read())

    @staticmethod
    @patch(OPEN, new_callable=MockOpen)
    def test_issue_4(mock_open):
        """Assert relative calls after consecutive opens."""
        with open('/path/to/file', 'r') as _:
            pass

        mock_open.reset_mock()

        with open('/path/to/file', 'r') as _:
            pass

        # The key here is that the last three calls objects are `call()`
        # instead of `call`. This is fixed by setting _new_name.
        mock_open.assert_has_calls([
            call('/path/to/file', 'r'),
            call().__enter__(),
            call().__exit__(None, None, None),
            call().close(),
        ])
