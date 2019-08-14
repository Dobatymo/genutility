from __future__ import absolute_import, division, print_function, unicode_literals

from builtins import map
from math import pow
from typing import TYPE_CHECKING

from .math import reciprocal
from .compat.math import prod

if TYPE_CHECKING:
	from collections.abc import Collection

def arithmetic_mean(col):
	# type: (Collection, ) -> float

	""" Arithmetic mean of `col`. """

	return sum(col) / len(col)

mean = arithmetic_mean

def harmonic_mean(col):
	# type: (Collection, ) -> float

	""" Harmonic mean of `col`. """

	return len(col) / sum(map(reciprocal, col))

def geometric_mean(col):
	# type: (Collection, ) -> float

	""" Geometric mean of `col`. """

	return pow(prod(col), reciprocal(len(col)))
