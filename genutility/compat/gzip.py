from __future__ import absolute_import, division, print_function, unicode_literals

from builtins import bytes, str
from future.utils import PY2

if PY2:

	import io
	from gzip import GzipFile

	from . import os

	""" This function is copied from `Python36\Lib\gzip.py`.
	"""

	def open(filename, mode="rb", compresslevel=9,
			 encoding=None, errors=None, newline=None):
		"""Open a gzip-compressed file in binary or text mode.

		The filename argument can be an actual filename (a str or bytes object), or
		an existing file object to read from or write to.

		The mode argument can be "r", "rb", "w", "wb", "x", "xb", "a" or "ab" for
		binary mode, or "rt", "wt", "xt" or "at" for text mode. The default mode is
		"rb", and the default compresslevel is 9.

		For binary mode, this function is equivalent to the GzipFile constructor:
		GzipFile(filename, mode, compresslevel). In this case, the encoding, errors
		and newline arguments must not be provided.

		For text mode, a GzipFile object is created, and wrapped in an
		io.TextIOWrapper instance with the specified encoding, error handling
		behavior, and line ending(s).

		"""
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

		gz_mode = mode.replace("t", "")
		if isinstance(filename, (str, bytes, os.PathLike)):
			binary_file = GzipFile(filename, gz_mode, compresslevel)
		elif hasattr(filename, "read") or hasattr(filename, "write"):
			binary_file = GzipFile(None, gz_mode, compresslevel, filename)
		else:
			raise TypeError("filename must be a str or bytes object, or a file")

		if "t" in mode:
			return io.TextIOWrapper(binary_file, encoding, errors, newline)
		else:
			return binary_file

else:
	from gzip import open
