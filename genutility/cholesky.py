from __future__ import absolute_import, division, print_function, unicode_literals

from math import sqrt

from .numba import opjit
from .numpy import is_square


@opjit(["void(f4[:,:], f4[:], f4)", "void(f8[:,:], f8[:], f8)"])
def _choldate(L, x, sign):

	for k in range(L.shape[0]):
		r = sqrt(L[k, k]*L[k, k] + sign * x[k]*x[k])
		c = r / L[k, k]
		s = x[k] / L[k, k]
		L[k, k] = r

		L[k+1:, k] = (L[k+1:, k] + sign * s * x[k+1:]) / c
		x[k+1:] = c * x[k+1:] - s * L[k+1:, k]

def choldate(L, x, sign):
	# type: (np.ndarray, np.ndarray, str) -> None

	""" This function computes the lower triangular Cholesky decomposition L' of matrix A' from L in-place
		(the cholesky decomp of A) where A' = A + sign*x*x^T.
		Based on: https://en.wikipedia.org/wiki/Cholesky_decomposition#Rank-one_update

		L: square lower triangular matrix
	"""

	if not is_square(L) or x.shape != (L.shape[0], ):
		raise ValueError("Invalid dimensions")

	try:
		sign = {"+": +1., "-": -1.}[sign]
	except KeyError:
		raise ValueError("Invalid sign")

	return _choldate(L, x, sign)

if __name__ == "__main__":
	import timeit

	import numpy as np

	from .numpy import random_triangular_matrix

	size = 100
	L = random_triangular_matrix(size)
	x = np.random.uniform(0, 1, size)

	choldate(L, x, "+") # warmup
	print(min(timeit.repeat('choldate(L, x, "+")', number=10000, repeat=5, globals=globals())))
