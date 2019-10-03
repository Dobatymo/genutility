from __future__ import absolute_import, division, print_function, unicode_literals

import numpy as np

from .numpy import normalize, categorical

class LDABase(object):

	def __init__(self):
		np.seterr(all="raise")

	def init_topic(self):
		# type: () -> int

		return np.random.randint(self.K)

	def add_counts(self, m, t, k):
		# type: (int, int, int) -> None

		self.nmk[m, k] += 1
		self.nm[m] += 1
		self.nkt[k, t] += 1
		self.nk[k] += 1

	def sub_counts(self, m, t, k):
		# type: (int, int, int) -> None

		self.nmk[m, k] -= 1
		self.nm[m] -= 1
		self.nkt[k, t] -= 1
		self.nk[k] -= 1

	def _initialize_topics(self, docs, topics):
		# type: (List[List[int]], dict) -> None

		for m, doc in enumerate(docs):
			for i, t in enumerate(doc):
				k = topics[m, i] = self.init_topic()
				self.add_counts(m, t, k)

	def calc_probs(self, m, t):
		# type: (int, int) -> float[K]

		# notes: np.sum(self.nkt, axis=-1) == self.nk
		# notes: np.sum(self.nmk[m], axis=-1) == self.nm[m]

		""" This is eq1. in the DC-LDA paper. """

		""" The α and β terms could be moved to `initialize`.
		"""

		""" The full term for left would be:
			left = (self.nmk[m,:] + self.α) / (self.nm[m] + self.αsum) # [K]
			however, the denominator can be dropped, because it doesn't depend on `k`
			and we only care about proportionality.
			It is done so in: 'A Theoretical and Practical
			Implementation Tutorial on Topic Modeling and Gibbs Sampling'
		"""

		left = (self.nmk[m,:] + self.α) # [K]
		right = (self.nkt[:,t] + self.β[t]) / (self.nk + self.βsum) # [K]
		return left * right # [K]

	def sample(self, m, t, k):
		# type: (int, int, int) -> int

		probs = self.calc_probs(m, t) # [K]
		return categorical(normalize(probs))

	def _sample_all(self, docs, topics):
		# type: (List[List[int]], dict) -> None

		for m, doc in enumerate(docs):
			for i, t in enumerate(doc):
				k = topics[m, i]
				self.sub_counts(m, t, k)
				k = topics[m, i] = self.sample(m, t, k) # sample new topics
				self.add_counts(m, t, k)

	def initialize_docs(self, docs):
		""" Set parameters based on input docs """

		raise NotImplementedError

	def initialize_topics(self): # step1
		""" Initialize topics matrix """

		raise NotImplementedError

	def sample_all(self): # step2 and step3
		# type: () -> None

		""" Sample new topics """

		raise NotImplementedError

	def metric(self):
		# type: () -> float

		raise NotImplementedError

	def fit(self, docs, n_iter=10, verbose=False):
		""" Fit LDA """

		self.initialize_docs(docs)
		self.initialize_topics()
		for i in range(n_iter):
			self.sample_all()
			if verbose:
				print("Step #{}, metric: {}".format(i, self.metric()))

	def theta(self):
		# type: () -> np.ndarray

		num = self.nmk + self.α # [M, K]
		denom = self.nm + self.αsum # [M]
		return num / denom[:,None] # [M, K]

	def phi(self):
		# type: () -> np.ndarray

		num = self.nkt + self.β # [K, V]
		denom = self.nk + self.βsum # [K]
		return num / denom[:,None] # [K, V]
