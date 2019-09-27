from __future__ import absolute_import, division, print_function, unicode_literals

import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.linalg import solve_triangular

def linear_sum_assignment_cost(cost_matrix):
	""" Minimum weight matching in bipartite graphs using the Hungarian/Kuhn-Munkres algorithm. """

	row_ind, col_ind = linear_sum_assignment(cost_matrix)
	return np.sum(cost_matrix[row_ind, col_ind])

def batch_solve_triangular(matrices, vectors, lower=False, overwrite_b=False):
	# type: (np.ndarray, np.ndarry, bool, bool) -> np.ndarray

	B, M1, M2 = matrices.shape
	B2, V = vectors.shape

	if B != B2 or M1 != M2 or M2 != V:
		raise ValueError("Input dimensions are invalid")

	out = np.empty_like(vectors)

	for i in range(B):
		out[i] = solve_triangular(matrices[i], vectors[i], lower=lower, overwrite_b=overwrite_b)

	return out
