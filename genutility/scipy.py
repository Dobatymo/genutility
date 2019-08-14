import numpy as np
from scipy.optimize import linear_sum_assignment

def linear_sum_assignment_cost(cost_matrix):
	""" Minimum weight matching in bipartite graphs using the Hungarian/Kuhn-Munkres algorithm. """

	row_ind, col_ind = linear_sum_assignment(cost_matrix)
	return np.sum(cost_matrix[row_ind, col_ind])
