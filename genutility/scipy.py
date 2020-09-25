from __future__ import absolute_import, division, print_function, unicode_literals

import numpy as np
from scipy.linalg import solve_triangular
from scipy.optimize import linear_sum_assignment

# from .numba import opjit

def linear_sum_assignment_cost(cost_matrix):
	""" Minimum weight matching in bipartite graphs using the Hungarian/Kuhn-Munkres algorithm. """

	row_ind, col_ind = linear_sum_assignment(cost_matrix)
	return np.sum(cost_matrix[row_ind, col_ind])

#@opjit(["f4[:,:](f4[:,:,:], f4[:,:], b1, b1, b1)", "f8[:,:](f8[:,:,:], f8[:,:], b1, b1, b1)"])
def batch_solve_triangular(matrices, vectors, lower=False, overwrite_b=False, check_finite=False):
	# type: (np.ndarray, np.ndarry, bool, bool, bool) -> np.ndarray

	B, M1, M2 = matrices.shape
	B2, V = vectors.shape

	if B != B2 or M1 != M2 or M2 != V:
		raise ValueError("Input dimensions are invalid")

	out = np.empty_like(vectors)

	for i in range(B):
		out[i] = solve_triangular(matrices[i], vectors[i], lower=lower, overwrite_b=overwrite_b, check_finite=check_finite)

	return out

if __name__ == "__main__":
	import timeit

	from .numpy import random_triangular_matrix

	size = 100
	bs = 200
	Ms = np.array([random_triangular_matrix(size, lower=True) for _ in range(bs)])
	vs = np.random.uniform(0, 1, (bs, size))

	batch_solve_triangular(Ms, vs, lower=True) # warmup
	print(min(timeit.repeat('batch_solve_triangular(Ms, vs, lower=True)', number=10, repeat=5, globals=globals())))
