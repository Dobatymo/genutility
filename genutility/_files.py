"""This module is to avoid circular imports.
It should avoid any dependencies apart from the standard library.
"""

import os
import os.path
import re
from typing import Optional, Union

from .typing import DirEntryProtocol

PathType = Union[str, os.PathLike]


class _DirEntry(os.PathLike):
    __slots__ = ("entry",)

    def __init__(
        self,
        name: str,
        path: Optional[str] = None,
        inode: Optional[int] = None,
        is_dir: Optional[bool] = None,
        is_file: Optional[bool] = None,
        is_symlink: Optional[bool] = None,
        stat: Optional[os.stat_result] = None,
    ) -> None:
        self.name = name
        self.path = name if path is None else path
        self._inode = inode
        self._is_dir = is_dir
        self._is_file = is_file
        self._is_symlink = is_symlink
        self._stat = stat

    def inode(self) -> int:
        assert self._inode is not None
        return self._inode

    def is_dir(self, follow_symlinks: bool = True) -> bool:
        assert self._is_dir is not None
        return self._is_dir

    def is_file(self, follow_symlinks: bool = True) -> bool:
        assert self._is_file is not None
        return self._is_file

    def is_symlink(self) -> bool:
        assert self._is_symlink is not None
        return self._is_symlink

    def stat(self, follow_symlinks: bool = True) -> os.stat_result:
        assert self._stat is not None
        return self._stat

    def __str__(self) -> str:
        return f"<_DirEntry {self.name!r}>"

    def __repr__(self) -> str:
        return str(self)

    def __fspath__(self) -> str:
        return self.path


class BaseDirEntry(os.PathLike):
    __slots__ = ("entry",)

    """ You cannot inherit from `os.DirEntry` (type 'nt.DirEntry' is not an acceptable base type),
        so use this wrapper class instead.
    """

    def __init__(self, entry: DirEntryProtocol) -> None:
        self.entry = entry

    @property
    def name(self) -> str:
        return self.entry.name

    @property
    def path(self) -> str:
        return self.entry.path

    def inode(self) -> int:
        return self.entry.inode()

    def is_dir(self, follow_symlinks=True) -> bool:
        return self.entry.is_dir(follow_symlinks=follow_symlinks)

    def is_file(self, follow_symlinks=True) -> bool:
        return self.entry.is_file(follow_symlinks=follow_symlinks)

    def is_symlink(self) -> bool:
        return self.entry.is_symlink()

    def stat(self, follow_symlinks=True) -> os.stat_result:
        return self.entry.stat(follow_symlinks=follow_symlinks)

    def __str__(self) -> str:
        return str(self.entry)

    def __repr__(self) -> str:
        return repr(self.entry)

    def __fspath__(self) -> str:
        return os.fspath(self.entry)


MyDirEntryT = Union[os.DirEntry, BaseDirEntry]


def entrysuffix(entry: MyDirEntryT) -> str:
    return os.path.splitext(entry.name)[1]


def to_dos_device_path(path: str) -> str:
    """Converts a standard absolute Windows path to a DOS device path aka local device paths.
    These paths are not normalized by the Win32 api and can be used to access otherwise unavailable files.
    """

    p = r"(?:(?:\\\\([^\\\/]+))|([a-z]:))([\\\/].*)"
    m = re.match(p, path, re.IGNORECASE)

    if m:
        server, drive, _path = m.groups()
        if drive is not None:
            return "\\\\?\\" + drive + _path
        elif server not in ("?", "."):
            return "\\\\?\\UNC\\" + server + _path

    return path


def to_dos_path(path: str) -> str:
    """Converts a DOS device path aka local device paths to a standard absolute Windows path.
    These paths have better compatibility and familiarity but also more limitations.
    """

    p = r"\\\\(?:\?|\.)\\(?:(unc\\)|([a-z]:))(.*)"
    m = re.match(p, path, re.IGNORECASE)
    if m:
        unc, drive, _path = m.groups()
        if unc:
            return "\\\\" + _path
        else:
            return drive + _path

    return path
