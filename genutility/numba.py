from __future__ import absolute_import, division, print_function, unicode_literals

from typing import TYPE_CHECKING

from .func import identity

if TYPE_CHECKING:
	from typing import Any, Callable

try:
	from numba import prange as oprange

except ImportError:
	from warnings import warn
	warn("Numba not found.", stacklevel=2)

	oprange = range

def opjit(*args, **kwargs):
	# type: (*Any, **Any) -> Callable

	""" Optional / opportunistic numba jit decorator. """

	try:
		from numba import njit

	except ImportError:
		from warnings import warn
		warn("Numba not found. Using slower pure Python version.", stacklevel=2)

		return identity

	kwargs.setdefault("fastmath", True)
	kwargs.setdefault("cache", True)

	def dec(func):
		return njit(*args, **kwargs)(func)

	return dec
