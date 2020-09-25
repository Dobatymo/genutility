from __future__ import absolute_import, division, print_function, unicode_literals

from future.utils import PY2

import os
import platform
from typing import TYPE_CHECKING

from .os_shared import is_os_64bit

if TYPE_CHECKING:
	from builtins import str

	from typing import Callable

system = platform.system()

class CurrentWorkingDirectory(object):

	__slots__ = ("oldcwd", )

	def __init__(self, path):
		self.oldcwd = os.getcwd()
		os.chdir(path)

	def close(self):
		os.chdir(self.oldcwd)

	def __enter__(self):
		return self

	def __exit__(self, exc_type, exc_value, traceback):
		self.close()

def rename(func_name):
	# type: (str, ) -> Callable

	if PY2:
		func_name = func_name.encode("ascii")

	def decorator(func):
		func.__name__ = func_name
		return func

	return decorator

def _not_available(func_name):
	# type: (str) -> None

	@rename(func_name)
	def inner(*args, **kwargs):
		raise OSError("{}() is not available for {}".format(func_name, system))

	return inner

if system == "Windows":

	from .os_win import _disk_usage_windows as disk_usage
	from .os_win import _filemanager_cmd_windows as filemanager_cmd
	from .os_win import _get_appdata_dir as get_appdata_dir
	from .os_win import _interrupt_windows as interrupt
	from .os_win import _islink as islink
	from .os_win import _lock as lock
	from .os_win import _uncabspath as uncabspath
	from .os_win import _unlock as unlock
	from .os_win import _volume_info_windows as volume_info

elif system == "Linux":

	from .os_posix import _disk_usage_posix as disk_usage
	from .os_posix import _lock as lock
	from .os_posix import _unlock as unlock
	volume_info = _not_available("volume_info")
	from .os_posix import _filemanager_cmd_posix as filemanager_cmd
	get_appdata_dir = _not_available("get_appdata_dir")
	from os.path import abspath as uncabspath
	from os.path import islink

	from .os_posix import _interrupt_posix as interrupt

elif system == "Darwin":

	from .os_posix import _disk_usage_posix as disk_usage
	from .os_posix import _lock as lock
	from .os_posix import _unlock as unlock
	volume_info = _not_available("volume_info")
	from .os_mac import _filemanager_cmd_mac as filemanager_cmd
	get_appdata_dir = _not_available("get_appdata_dir")
	from os.path import abspath as uncabspath
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
	uncabspath = _not_available("uncabspath")
	interrupt = _not_available("interrupt")

lock.__doc__ = """ Locks access to the file (on Posix) or its contents (Windows). """
unlock.__doc__ = """ Unlocks access to the file. """
disk_usage.__doc__ = """ Returns (total, used, free) bytes on disk. """
volume_info.__doc__ = """ filesystem and name of the volume """
filemanager_cmd.__doc__ = """ Returns a shell command that when executed starts the file manager of the OS. """
get_appdata_dir.__doc__ = """ Returns the roaming appdata directory of the current user. """
islink.__doc__ = """ islink """
uncabspath.__doc__ = """ uncabspath """
interrupt.__doc__ = """ interrupt """

import sys

if sys.version_info >= (3, 3):
	from shutil import disk_usage
