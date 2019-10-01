import numpy as np

class LDABase(object):

	def __init__(self):
		np.seterr(all="raise")

	def initialize_docs(self, docs):
		""" Set parameters based on input docs """

		raise NotImplementedError

	def initialize_topics(self): # step1
		""" Initialize topics matrix """

		raise NotImplementedError

	def sample_all(self): # step2 and step3
		""" Sample new topics """

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
		raise NotImplementedError

	def phi(self):
		raise NotImplementedError
