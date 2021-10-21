from __future__ import generator_stop

import os.path
from os import DirEntry
from typing import Union

""" This module is to avoid circular imports.
	It should avoid any dependencies apart from the standard library.
"""

class BaseDirEntry:
	__slots__ = ("entry", )

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

def entrysuffix(entry):
	# type: (MyDirEntryT, ) -> str

	return os.path.splitext(entry.name)[1]
