from __future__ import absolute_import, division, print_function, unicode_literals

from math import sqrt

from .numpy import issquare

def choldate(L, x, sign):
	# type: (np.ndarray, np.ndarray, str) -> None

	""" This function computes the lower triangular Cholesky decomposition L' of matrix A' from L in-place
		(the cholesky decomp of A) where A' = A + sign*x*x^T.
		Based on: https://en.wikipedia.org/wiki/Cholesky_decomposition#Rank-one_update

		L: square lower triangular matrix
	"""

	if not issquare(L) or x.shape != (L.shape[0], ):
		raise ValueError("Invalid dimensions")

	try:
		sign = {"+": +1, "-": -1}[sign]
	except KeyError:
		raise ValueError("Invalid sign")

	for k in range(L.shape[0]):
		r = sqrt(L[k, k]*L[k, k] + sign * x[k]*x[k])
		c = r / L[k, k]
		s = x[k] / L[k, k]
		L[k, k] = r

		L[k+1:, k] = (L[k+1:, k] + sign * s * x[k+1:]) / c
		x[k+1:] = c * x[k+1:] - s * L[k+1:, k]
