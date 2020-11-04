from __future__ import absolute_import, division, print_function, unicode_literals

from builtins import bytes, str
from future.utils import PY2

import os.path
from io import open
from os import remove
from sys import getfilesystemencoding
from tempfile import mkstemp
from typing import TYPE_CHECKING

from .compat.os import fspath, replace
from .file import copen

if TYPE_CHECKING:
	from typing import IO, ContextManager, Optional, Union

	from .compat.os import PathLike
	PathType = Union[str, PathLike]

# http://stupidpythonideas.blogspot.tw/2014/07/getting-atomic-writes-right.html
class TransactionalCreateFile(object):

	def __init__(self, path, mode="wb", encoding=None, errors=None, newline=None, prefix="tmp"):
		# type: (PathType, str, Optional[str], Optional[str], Optional[str], str) -> None

		is_text = "t" in mode

		self.path = fspath(path)
		suffix = os.path.splitext(self.path)[1].lower()
		curdir = os.path.dirname(self.path)
		fd, self.tmppath = mkstemp(suffix, prefix, curdir, is_text)
		if PY2:
			self.tmppath = self.tmppath.decode(getfilesystemencoding())

		self.fp = copen(fd, mode, encoding=encoding, errors=errors, newline=newline, ext=suffix)

	def commit(self):
		# type: () -> None

		self.fp.close()
		replace(self.tmppath, self.path) # should be atomic

	def rollback(self):
		# type: () -> None

		self.fp.close()
		remove(self.tmppath)

	def __enter__(self):
		# type: () -> IO

		return self.fp

	def __exit__(self, exc_type, exc_value, traceback):
		# at this point the original file is unmodified and the new file exists as tempfile on disk (or in buffer on windows)
		if exc_type:
			self.rollback()
		else:
			self.commit()

def sopen(path, mode="rb", encoding=None, errors=None, newline=None, safe=False):
	# type: (PathType, str, Optional[str], Optional[str], Optional[str], bool) -> ContextManager[IO]

	if safe:
		return TransactionalCreateFile(path, mode, encoding=encoding, errors=errors, newline=newline)
	else:
		return copen(path, mode, encoding=encoding, errors=errors, newline=newline)

def write_file(data, path, mode="wb", encoding=None, errors=None, newline=None):
	# type: (Union[str, bytes], PathType, str, Optional[str], Optional[str], Optional[str]) -> None

	""" Writes/overwrites files in a safe way. That means either the original file
		will be left untouched, or it will be replaced with the complete new file.
	"""

	with TransactionalCreateFile(path, mode, encoding=encoding, errors=errors, newline=newline) as fw:
		fw.write(data)
