""" This module is to avoid circular imports.
    It should avoid any dependencies apart from the standard library.
"""

from __future__ import generator_stop

import os.path
import re
from os import DirEntry, PathLike
from typing import Union

PathType = Union[str, PathLike]


class BaseDirEntry:
    __slots__ = ("entry",)

    def __init__(self, entry):
        self.entry = entry

    @property
    def name(self):
        return self.entry.name

    @property
    def path(self):
        return self.entry.path

    def inode(self):
        return self.entry.inode()

    def is_dir(self):
        return self.entry.is_dir()

    def is_file(self):
        return self.entry.is_file()

    def is_symlink(self):
        return self.entry.is_symlink()

    def stat(self):
        return self.entry.stat()

    def __str__(self):
        return str(self.entry)

    def __repr__(self):
        return repr(self.entry)

    def __fspath__(self):
        return self.entry.path


MyDirEntryT = Union[DirEntry, BaseDirEntry]


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
