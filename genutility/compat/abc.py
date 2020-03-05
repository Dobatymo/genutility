from __future__ import absolute_import, division, print_function, unicode_literals

import sys

if sys.version_info >= (3, 0):
	from abc import ABC
else:
	from abc import ABCMeta
	ABC = ABCMeta(b"ABC", (object,), {"__slots__": ()})
