"""Mock classes for open() and the file type."""

import sys
from os import SEEK_SET, SEEK_END
from io import TextIOWrapper

try:
    # pylint: disable=no-name-in-module
    from unittest.mock import Mock, NonCallableMock, DEFAULT
except ImportError:
    from mock import Mock, NonCallableMock, DEFAULT

if sys.version_info < (3, 0):
    try:
        from cStringIO import StringIO, StringIO as BytesIO
    except ImportError:
        from StringIO import StringIO, StringIO as BytesIO
else:
    from io import StringIO, BytesIO


class FileLikeMock(NonCallableMock):
    """Acts like a file object returned from open()."""
    def __init__(self, name=None, read_data='', *args, **kws):
        kws.update({'spec': TextIOWrapper, })
        super(FileLikeMock, self).__init__(*args, **kws)
        self.mode = None
        self.__is_closed = False
        self.read_data = read_data
        self.close.side_effect = self._close

        self.__enter__ = Mock(side_effect=self._enter)
        self.__exit__ = Mock(side_effect=self._exit)

        if name is not None:
            self.name = name

    @property
    def closed(self):
        # pylint: disable=missing-docstring
        return self.__is_closed

    @property
    def read_data(self):
        """Bypass read function to access the contents of the file.

        This property should be used for testing purposes.
        """
        return self.__contents.getvalue()

    @read_data.setter
    def read_data(self, contents):
        # pylint: disable=missing-docstring
        # pylint: disable=attribute-defined-outside-init
        if isinstance(contents, str):
            self.__contents = StringIO()
        else:
            self.__contents = BytesIO()

        # Constructing a cStrinIO object with the input string would result
        # in a read-only object, so we write the contents after construction.
        self.__contents.write(contents)

        # Set tell/read/write/etc side effects to access the new contents
        # object.
        self.tell._mock_wraps = self.__contents.tell
        self.seek._mock_wraps = self.__contents.seek
        self.read._mock_wraps = self.__contents.read
        self.readline._mock_wraps = self.__contents.readline
        self.readlines._mock_wraps = self.__contents.readlines
        self.write._mock_wraps = self.__contents.write
        self.writelines._mock_wraps = self.__contents.writelines

    def __iter__(self):
        return iter(self.__contents)

    def __next__(self):
        current_position = self.__contents.tell()
        self._reset_position(0, SEEK_END)
        eof = self.__contents.tell()
        if eof <= current_position:
            raise StopIteration()

        self._reset_position(current_position)
        return self.readline()

    if sys.version_info < (3, 0):
        def next(self):
            return self.__next__()

    def set_properties(self, path, mode):
        """Set file's properties (name and mode).

        This function is also in charge of swapping between textual and
        binary streams.
        """
        if mode is None:
            mode = 'r'
        self.name = path
        self.mode = mode

        if 'b' in self.mode:
            if not isinstance(self.read_data, bytes):
                self.read_data = bytes(self.read_data, encoding='utf8')
        else:
            if not isinstance(self.read_data, str):
                self.read_data = str(self.read_data, encoding='utf8')

    def reset_mock(self, visited=None):
        """Reset the default tell/read/write/etc side effects."""
        # In some versions of the mock library, `reset_mock` takes an argument
        # and in some it doesn't. We try to handle all situations.
        if visited is not None:
            super(FileLikeMock, self).reset_mock(visited)
        else:
            super(FileLikeMock, self).reset_mock()

        # Reset contents and tell/read/write/close side effects.
        self.read_data = ''
        self.close.side_effect = self._close

    def _reset_position(self, position=0, whence=SEEK_SET):
        """A shortcut to `_contents`'s `seek` for internal use."""
        self.__contents.seek(position, whence)

    def _enter(self):
        """Reset the position in buffer according to the mode whenever entering context."""
        if 'a' in self.mode:
            self._reset_position(0, SEEK_END)
        else:
            self._reset_position()
        return self

    def _exit(self, exception_type, exception, traceback):
        """Close file when exiting context."""
        # pylint: disable=unused-argument
        self.close()

    def _close(self):
        """Mark file as closed (used for side_effect)."""
        self.__is_closed = True
        return DEFAULT


class MockOpen(Mock):
    """A mock for the open() builtin function."""
    def __init__(self, read_data='', *args, **kws):
        kws.update({'spec': open, 'name': open.__name__, })
        super(MockOpen, self).__init__(*args, **kws)
        self.__files = {}
        self.__read_data = read_data

    def __call__(self, path, mode=None, *args, **kws):
        original_side_effect = self._mock_side_effect

        if path in self.__files:
            self._mock_return_value = self.__files[path]
            self._mock_side_effect = self._mock_return_value.side_effect

        try:
            if mode is not None:
                child = super(MockOpen, self).__call__(path, mode, *args, **kws)
            else:
                child = super(MockOpen, self).__call__(path, *args, **kws)
        finally:
            # Reset the side effect after each call so that the next call to
            # open() won't cause the same side_effect.
            self._mock_side_effect = original_side_effect

        # Consecutive calls to open() set `return_value` to the last file mock
        # created. If the paths differ (and child isn't a newly-created mock,
        # evident by its name attribute being unset) we create a new file mock
        # instead of returning the previous one.
        if not isinstance(child.name, Mock) and path != child.name:
            child = self._get_child_mock(_new_name='()', name=path)
            self.__files[path] = child

        child.set_properties(path, mode)

        if path not in self.__files:
            self.__files[path] = child

        # Each call to `open` should reset the position in the file according to the mode.
        if mode and 'a' in mode:
            self.__files[path]._reset_position(0, SEEK_END)
        else:
            self.__files[path]._reset_position()

        self._mock_return_value = child
        return child

    def __getitem__(self, path):
        return self.__files.setdefault(path, self._get_child_mock(name=path))

    def __setitem__(self, path, value):
        value.__enter__ = lambda self: self
        value.__exit__ = lambda self, *args: None
        self.__files[path] = value

    def reset_mock(self, visited=None):
        # See comment in `FileLikeMock.reset_mock`.
        if visited is not None:
            super(MockOpen, self).reset_mock(visited)
        else:
            super(MockOpen, self).reset_mock()

        self.__files = {}
        self.__read_data = ''

    def _get_child_mock(self, **kws):
        """Create a new FileLikeMock instance.

        The new mock will inherit the parent's side_effect and read_data
        attributes.
        """
        kws.update({
            '_new_parent': self,
            'side_effect': self._mock_side_effect,
            'read_data': self.__read_data,
        })
        return FileLikeMock(**kws)
