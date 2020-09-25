from __future__ import absolute_import, division, print_function, unicode_literals

import bz2
import warnings
from io import TextIOWrapper

"""
most of this file is copied and modified from Python35/Lib/bz2.py file
"""

"""
import threading
tl = threading.local()
tl.indent = 0
"""

from future.utils import PY2

if PY2:
	warnings.warn("Python2 bz2 module does not support multiple streams", ImportWarning, stacklevel=2)

	class BZ2File3(bz2.BZ2File):

		"""
		Changed in version 3.1: Support for the with statement was added.
		Changed in version 3.3: The fileno(), readable(), seekable(), writable(), read1() and readinto() methods were added.
		"""

		def __init__(self, filename, mode="r", buffering=0, compresslevel=9):
			bz2.BZ2File.__init__(self, filename, mode, buffering, compresslevel)

		def _check_not_closed(self):
			if self.closed:
				raise ValueError("I/O operation on closed file")

		"""
		def __getattribute__(self, name):
			import logging
			attr = object.__getattribute__(self, name)
			if callable(attr):
				def wrapper(*args, **kwargs):
					try:
						indent = tl.indent
						tl.indent += 1
						ret = attr(*args, **kwargs)
						tl.indent -= 1
						logging.warning("%s%s(%s, %s): %s", "--"*indent, name, args, kwargs, ret)
						return ret
					except Exception as e:
						logging.exception(name)
						raise
				return wrapper
			else:
				return attr
		"""

		def fileno(self):
			raise RuntimeError("Method not available")

		def seekable(self):
			return self.readable()

		def readable(self):
			self._check_not_closed()
			return "r" in self.mode

		def writable(self):
			self._check_not_closed()
			return "w" in self.mode

		def flush(self):  # needed by fileinput.py
			pass

		def read1(self, size=-1):
			return self.read(size)

		def readinto(self, b):
			raise RuntimeError("Method not available")

		def __enter__(self):
			return self

		def __exit__(self, exc_type, exc_value, traceback):
			self.close()

	def open(filename, mode="rb", compresslevel=9, encoding=None, errors=None, newline=None):

		if "t" in mode:
			if "b" in mode:
				raise ValueError("Invalid mode: %r" % (mode,))
		else:
			if encoding is not None:
				raise ValueError("Argument 'encoding' not supported in binary mode")
			if errors is not None:
				raise ValueError("Argument 'errors' not supported in binary mode")
			if newline is not None:
				raise ValueError("Argument 'newline' not supported in binary mode")

		bz_mode = mode.replace("t", "")
		binary_file = BZ2File3(filename, bz_mode, compresslevel=compresslevel)

		if "t" in mode:
			return TextIOWrapper(binary_file, encoding, errors, newline)
		else:
			return binary_file

else:
	open = bz2.open
