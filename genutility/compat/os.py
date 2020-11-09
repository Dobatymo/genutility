from __future__ import absolute_import, division, print_function, unicode_literals

from builtins import bytes, str
from future.utils import PY2

from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from typing import Union

if PY2:
	from io import TextIOWrapper
	from os import fdopen as _fdopen

	class _FileWrapper(object):
		def __init__(self, raw):
			self._raw = raw

		def readable(self):
			return True

		def writable(self):
			return True

		def seekable(self):
			return True

		def __getattr__(self, name):
			return getattr(self._raw, name)

	def fdopen(file, mode, encoding, errors, newline):
		bf = _fdopen(file, mode)

		# copy pasted from genutility.file.wrap_text
		if "t" in mode:
			f = _FileWrapper(bf)
			tf = TextIOWrapper(f, encoding, errors, newline)
			tf.mode = mode
			return tf
		return bf

else:
	from os import fdopen

try:
	from os import makedirs

except ImportError:
	import errno
	import os

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
		from os import rename as replace  # on posix rename can already replace existing files atomically

try:
	from os import DirEntry

except ImportError:
	from os import scandir
	DirEntry = type(next(scandir()))

try:
	from os import fspath

except ImportError:

	def fspath(path):

		if isinstance(path, (bytes, str)):
			return path

		try:
			path = path.__fspath__()
			if isinstance(path, (bytes, str)):
				return path

		except AttributeError:
			pass

		raise TypeError("Not a path-like object")
