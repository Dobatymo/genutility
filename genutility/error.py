from __future__ import absolute_import, division, print_function, unicode_literals

from functools import wraps
from warnings import warn


def deprecated(msg, stacklevel=2):
	def decorator(func):
		@wraps(func)
		def inner(*args, **kwargs):
			warn(msg, DeprecationWarning, stacklevel)
			print("DeprecationWarning:", msg)
			return func(*args, **kwargs)
		return inner
	return decorator
