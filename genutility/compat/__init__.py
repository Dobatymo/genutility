from __future__ import absolute_import, division, print_function, unicode_literals

try:
	from builtins import FileExistsError
except ImportError:
	class FileExistsError(IOError):
		pass
