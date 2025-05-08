import errno
import locale
import os
import stat
from contextlib import contextmanager
from io import BytesIO, StringIO
from os import strerror
from typing import IO, Iterator, List, NamedTuple, Optional, Tuple

from typing_extensions import Self

if hasattr(locale, "getencoding"):
    DEFAULT_ENCODING = locale.getencoding()
else:
    DEFAULT_ENCODING = locale.getpreferredencoding(False)


def file_not_found_error(*args):
    """return FileNotFoundError"""

    return OSError(errno.ENOENT, strerror(errno.ENOENT), *args)


def not_a_directory_error(*args):
    """return NotADirectoryError"""

    return OSError(errno.ENOTDIR, strerror(errno.ENOTDIR), *args)


def file_exists_error(*args):
    """return FileExistsError"""

    return OSError(errno.EEXIST, strerror(errno.EEXIST), *args)


def is_a_directory_error(*args):
    """return IsADirectoryError"""

    return OSError(errno.EISDIR, strerror(errno.EISDIR), *args)


def directory_not_empty_error(*args):
    """return OSError"""

    return OSError(errno.ENOTEMPTY, strerror(errno.ENOTEMPTY), *args)


class StatResult(NamedTuple):
    st_mode: int
    st_ino: int
    st_dev: int = 0
    st_nlink: Optional[int] = None
    st_uid: Optional[int] = None
    st_gid: Optional[int] = None
    st_size: Optional[int] = None
    st_atime: Optional[int] = None
    st_mtime: Optional[int] = None
    st_ctime: Optional[int] = None
    st_atime_ns: Optional[int] = None
    st_mtime_ns: Optional[int] = None
    st_ctime_ns: Optional[int] = None


class MemoryPurePath:
    def joinpath(self, *pathsegments: str) -> Self:
        raise NotImplementedError


class MemoryPath(MemoryPurePath):
    __slots__ = ("_data", "_children")

    _data: Optional[bytes]
    children: "Optional[List[MemoryPath]]"

    def __init__(self, data: Optional[bytes] = None, children: "Optional[List[MemoryPath]]" = None) -> None:
        if data is not None and children is not None:
            raise ValueError("A path cannot have data and children")

        self._data = data
        self._children = children

    # Parsing and generating URIs

    @classmethod
    def from_uri(cls, uri: str) -> Self:
        raise NotImplementedError

    def as_uri(self) -> str:
        raise NotImplementedError

    # Expanding and resolving paths

    @classmethod
    def home(cls) -> Self:
        raise NotImplementedError

    def expanduser(self) -> Self:
        raise NotImplementedError

    @classmethod
    def cwd(cls) -> Self:
        raise NotImplementedError

    def absolute(self) -> Self:
        raise NotImplementedError

    def resolve(self, strict: bool = False) -> Self:
        raise NotImplementedError

    def readlink(self) -> Self:
        raise NotImplementedError

    # Querying file type and status

    def stat(self, *, follow_symlinks: bool = True) -> StatResult:
        if self._data is None and self._children is None:
            raise file_not_found_error(str(self))

        if self._children is not None:
            st_mode: int = stat.S_IFDIR
            st_ino = id(self)
            st_size = None
        else:
            assert self._data is not None  # for mypy
            st_mode = stat.S_IFREG
            st_ino = id(self)
            st_size = len(self._data)

        return StatResult(st_mode=st_mode, st_ino=st_ino, st_size=st_size)

    def lstat(self) -> os.stat_result:
        raise NotImplementedError

    def exists(self, *, follow_symlinks: bool = True) -> bool:
        return self._data is not None or self._children is not None

    def is_file(self, *, follow_symlinks: bool = True) -> bool:
        return self._data is not None

    def is_dir(self, *, follow_symlinks: bool = True) -> bool:
        return self._children is not None

    def is_symlink(self) -> bool:
        return False

    def is_junction(self) -> bool:
        return False

    def is_mount(self) -> bool:
        return False

    def is_socket(self) -> bool:
        return False

    def is_fifo(self) -> bool:
        return False

    def is_block_device(self) -> bool:
        return False

    def is_char_device(self) -> bool:
        return False

    def samefile(self, other: "MemoryPath") -> bool:
        return self is other

    # Reading and writing files

    @contextmanager
    def open(
        self,
        mode: str = "r",
        buffering: int = -1,
        encoding: Optional[str] = None,
        errors: Optional[str] = None,
        newline: Optional[str] = None,
    ) -> Iterator[IO]:
        if "w" not in mode and self._data is None:
            raise file_not_found_error(str(self))

        if "b" in mode:
            if encoding is not None or errors is not None or newline is not None:
                raise ValueError("encoding, errors and newline cannot by used for bytes")

            if self._data is None:
                bdata = b""
            else:
                bdata = self._data

            with BytesIO(bdata) as fp:
                yield fp
                self._data = fp.getvalue()
        else:
            if encoding is None:
                encoding = DEFAULT_ENCODING

            if errors is None:
                errors = "strict"

            if self._data is None:
                sdata = ""
            else:
                sdata = self._data.decode(encoding, errors)

            with StringIO(sdata, newline) as fp:
                yield fp
                self._data = fp.getvalue().encode(encoding, errors)

    def read_text(
        self, encoding: Optional[str] = None, errors: Optional[str] = None, newline: Optional[str] = None
    ) -> str:
        # new line param is ignored

        if self._children is not None:
            raise is_a_directory_error(str(self))

        if self._data is None:
            raise file_not_found_error(str(self))

        if encoding is None:
            encoding = DEFAULT_ENCODING

        if errors is None:
            errors = "strict"

        return self._data.decode(encoding, errors)

    def read_bytes(self) -> bytes:
        if self._children is not None:
            raise is_a_directory_error(str(self))

        if self._data is None:
            raise file_not_found_error(str(self))

        return self._data

    def write_text(self, data: str, encoding=None, errors=None, newline=None) -> None:
        # new line param is ignored

        if self._children is not None:
            raise is_a_directory_error(str(self))

        if encoding is None:
            encoding = DEFAULT_ENCODING

        if errors is None:
            errors = "strict"

        self._data = data.encode(encoding, errors)

    def write_bytes(self, data: bytes) -> None:
        if self._children is not None:
            raise is_a_directory_error(str(self))

        self._data = data

    # Reading directories

    def iterdir(self) -> "Iterator[MemoryPath]":
        if self._data is not None:
            raise not_a_directory_error(str(self))

        if self._children is None:
            raise file_not_found_error(str(self))

        yield from self._children

    def glob(
        self, pattern, *, case_sensitive: Optional[bool] = None, recurse_symlinks: bool = False
    ) -> "Iterator[MemoryPath]":
        raise NotImplementedError

    def rglob(
        self, pattern, *, case_sensitive: Optional[bool] = None, recurse_symlinks: bool = False
    ) -> "Iterator[MemoryPath]":
        raise NotImplementedError

    def walk(
        self, top_down=True, on_error=None, follow_symlinks: bool = False
    ) -> "Iterator[Tuple[MemoryPath, List[str], List[str]]]":
        raise NotImplementedError

    # Creating files and directories

    def touch(self, mode: int = 0o666, exist_ok: bool = True) -> None:
        if self._children is not None:
            raise file_exists_error(str(self))

        if self._data is None:
            self._data = b""
        elif not exist_ok:
            raise file_exists_error(str(self))

    def mkdir(self, mode: int = 0o777, parents: bool = False, exist_ok: bool = False) -> None:
        if self._data is not None:
            raise file_exists_error(str(self))

        if self._children is None:
            self._children = []
        elif not exist_ok:
            raise file_exists_error(str(self))

    def symlink_to(self, target: str, target_is_directory: bool = False) -> None:
        raise NotImplementedError

    def hardlink_to(self, target: str) -> None:
        raise NotImplementedError

    # Renaming and deleting

    def rename(self, target: str) -> Self:
        raise NotImplementedError

    def replace(self, target: str) -> Self:
        raise NotImplementedError

    def unlink(self, missing_ok: bool = False) -> None:
        if self._children is not None:
            raise is_a_directory_error(str(self))

        if self._data is None:
            if missing_ok:
                return
            raise file_not_found_error(str(self))

        self._data = None

    def rmdir(self) -> None:
        if self._data is not None:
            raise not_a_directory_error(str(self))

        if self._children is None:
            raise file_not_found_error(str(self))

        if self._children:
            raise directory_not_empty_error(str(self))

        self._children = None
