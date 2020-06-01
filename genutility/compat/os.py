from __future__ import absolute_import, division, print_function, unicode_literals

from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from typing import Union

try:
	from os import makedirs

except ImportError:
	import os, errno

	def makedirs(name, mode=0o777, exist_ok=False):
		try:
			return os.makedirs(str(name), mode)
		except OSError as e:
			if exist_ok and e.errno == errno.EEXIST:
				pass
			else:
				raise

try:
	from os import PathLike

except ImportError:
	from abc import abstractmethod
	from .abc import ABC

	class PathLike(ABC):

		"""Abstract base class for implementing the file system path protocol."""

		@abstractmethod
		def __fspath__(self):
			"""Return the file system path representation of the object."""
			raise NotImplementedError

		@classmethod
		def __subclasshook__(cls, subclass):
			return hasattr(subclass, "__fspath__")

try:
	from os import replace

except ImportError:

	import sys

	if sys.platform == "win32":
		from ctypes import WinError
		from cwinsdk.um.WinBase import MOVEFILE_REPLACE_EXISTING

		def replace(src, dst):
			# type: (Union[str, bytes], Union[str, bytes]) -> None

			if isinstance(src, str) and isinstance(dst, str):
				from cwinsdk.um.WinBase import MoveFileExW as MoveFileEx
			elif isinstance(src, bytes) and isinstance(dst, bytes):
				from cwinsdk.um.WinBase import MoveFileExA as MoveFileEx
			else:
				raise ValueError("Arguments must be both bytes or both string")

			if MoveFileEx(src, dst, MOVEFILE_REPLACE_EXISTING) == 0:
				raise WinError()

	else:
		from os import rename as replace # on posix rename can already replace existing files atomically

try:
	from os import scandir as _scandir
except ImportError:
	from scandir import scandir as _scandir

if hasattr(_scandir, "__exit__"):
	scandir = _scandir
else:
	class scandir(object):

		def __init__(self, path="."):
			self.it = _scandir(path)

		def __enter__(self):
			return self.it

		def __exit__(self, *args):
			pass

		def __iter__(self):
			return self.it

		def __next__(self):
			return next(self.it)

		next = __next__

try:
	from os import DirEntry

except ImportError:
	DirEntry = type(next(scandir()))

try:
	from os import fspath

except ImportError:

	fspath = str # bad, but at least works for `Path`s.
