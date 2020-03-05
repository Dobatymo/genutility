from __future__ import absolute_import, division, print_function, unicode_literals

from sys import version_info

if version_info >= (3, 2):
	from os import makedirs
else:
	import os, errno

	def makedirs(name, mode=0o777, exist_ok=False):
		try:
			return os.makedirs(str(name), mode)
		except OSError as e:
			if exist_ok and e.errno == errno.EEXIST:
				pass
			else:
				raise

if version_info >= (3, 6):
	from os import PathLike
else:
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
