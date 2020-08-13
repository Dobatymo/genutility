from __future__ import absolute_import, division, print_function, unicode_literals

try:
	from builtins import FileNotFoundError
except ImportError:
	FileNotFoundError = OSError

try:
	from builtins import FileExistsError
except ImportError:
	FileExistsError = OSError
