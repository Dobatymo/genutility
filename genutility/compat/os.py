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
