from __future__ import generator_stop

import os
import platform
from pathlib import Path
from typing import Callable, Union

from ._func import rename
from .os_shared import is_os_64bit  # noqa: F401

PathStr = Union[Path, str]

system = platform.system()


class CurrentWorkingDirectory:

    __slots__ = ("oldcwd",)

    def __init__(self, path: PathStr) -> None:

        self.oldcwd = os.getcwd()
        os.chdir(path)

    def close(self) -> None:

        os.chdir(self.oldcwd)

    def __enter__(self) -> "CurrentWorkingDirectory":
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


def _not_available(func_name: str) -> Callable:
    @rename(func_name)
    def inner(*args, **kwargs):
        raise OSError(f"{func_name}() is not available for {system}")

    return inner


if system == "Windows":

    from .os_win import _disk_usage_windows as disk_usage
    from .os_win import _filemanager_cmd_windows as filemanager_cmd
    from .os_win import _get_appdata_dir as get_appdata_dir
    from .os_win import _interrupt_windows as interrupt
    from .os_win import _islink as islink
    from .os_win import _lock as lock
    from .os_win import _unlock as unlock
    from .os_win import _volume_info_windows as volume_info

elif system == "Linux":

    from .os_posix import _disk_usage_posix as disk_usage
    from .os_posix import _get_appdata_dir as get_appdata_dir
    from .os_posix import _lock as lock
    from .os_posix import _unlock as unlock

    volume_info = _not_available("volume_info")
    from os.path import islink

    from .os_posix import _filemanager_cmd_posix as filemanager_cmd
    from .os_posix import _interrupt_posix as interrupt

elif system == "Darwin":

    from .os_posix import _disk_usage_posix as disk_usage
    from .os_posix import _lock as lock
    from .os_posix import _unlock as unlock

    volume_info = _not_available("volume_info")
    from .os_mac import _filemanager_cmd_mac as filemanager_cmd

    get_appdata_dir = _not_available("get_appdata_dir")
    from os.path import islink

    from .os_posix import _interrupt_posix as interrupt

else:
    lock = _not_available("lock")
    unlock = _not_available("unlock")
    disk_usage = _not_available("disk_usage")
    volume_info = _not_available("volume_info")
    filemanager_cmd = _not_available("filemanager_cmd")
    get_appdata_dir = _not_available("get_appdata_dir")
    islink = _not_available("islink")
    interrupt = _not_available("interrupt")

lock.__doc__ = """ Locks access to the file (on Posix) or its contents (Windows). """
unlock.__doc__ = """ Unlocks access to the file. """
disk_usage.__doc__ = """ Returns (total, used, free) bytes on disk. """
volume_info.__doc__ = """ filesystem and name of the volume """
filemanager_cmd.__doc__ = """ Returns a shell command that when executed starts the file manager of the OS. """
get_appdata_dir.__doc__ = """ Returns the roaming appdata directory of the current user. """
islink.__doc__ = """ islink """
interrupt.__doc__ = """ interrupt """

from shutil import disk_usage
