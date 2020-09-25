from __future__ import absolute_import, division, print_function, unicode_literals

from future.utils import PY2

import sys

if PY2:
	def tofs(s):
		return s.encode(sys.getfilesystemencoding())

	def fromfs(b):
		return b.decode(sys.getfilesystemencoding())

	def sbs(s):
		return s.encode("ascii")

else:
	def tofs(s):
		return s

	def fromfs(b):
		return b

	def sbs(s):
		return s
