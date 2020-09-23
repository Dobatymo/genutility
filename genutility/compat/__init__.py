from __future__ import absolute_import, division, print_function, unicode_literals

try:
	from builtins import FileNotFoundError
except ImportError:
	FileNotFoundError = OSError  # type: ignore

try:
	from builtins import FileExistsError
except ImportError:
	FileExistsError = OSError  # type: ignore
