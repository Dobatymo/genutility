from __future__ import absolute_import, division, print_function, unicode_literals

import numpy as np

class LinearRegression(object):

	""" Linear regression optimized by gradient descent. """

	def __init__(self, X, y, alpha=0.01):
		# type: (float[A, B], float[A], float) -> None

		assert len(X.shape) == 2

		self.K = X.shape[1] + 1  # one extra dimension for the bias term
		self.M = len(y)
		self.y = y
		self.α = alpha

		row = np.ones((self.M, 1))
		self.X = np.concatenate([row, X], axis=-1)
		assert self.X.shape == (self.M, self.K)

		self.weights = np.random.random_sample(self.K)

	def predict(self, x):
		# type: (float[B], ) -> float

		return np.matmul(x, self.weights)

	def epoch(self):
		# type: () -> None

		self.weights -= self.α * np.matmul(self.X.T, self.predict(self.X) - self.y) # [K]

	def fit(self, n_iter=100, verbose=False):
		# type: () -> None

		for i in range(n_iter):
			if verbose:
				print("SGD itertion:", i)
			self.epoch()

	def getParams(self):
		# type: () -> float[B-1]

		return self.weights[1:]

	def getIntercept(self):
		# type: () -> float

		return self.weights[0]
