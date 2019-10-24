from __future__ import absolute_import, division, print_function, unicode_literals

from math import log2, exp
from itertools import chain
from collections import Counter
from sys import stderr
from typing import TYPE_CHECKING

import numpy as np

from .numpy import normalize, categorical, batchtopk
from .datastructures import VariableRowMatrix
from .encoder import BatchLabelEncoder
from .iter import count_distinct
from .sequence import LasyStringList
from .object import cast

if TYPE_CHECKING:
	from typing import Any, Dict, Iterable
	Documents = List[List[int]]
	IterableDocuments = Iterable[Iterable[int]]

# utils

def mylen(obj):
	from scipy.sparse import issparse

	if issparse(obj):
		return obj.shape[0]
	else:
		return len(obj)

def top_topics(id2word, term_topic_matrix, num_words=10, decimals=2):
	# type: (Dict[int, str], float[K, V], int) -> Iterator[List[Tuple[str, float]]]

	indices_list, probs_list = batchtopk(term_topic_matrix, num_words, reverse=True)
	np.around(probs_list, decimals=2, out=probs_list)

	for indices, probs in zip(indices_list, probs_list):
		yield [(id2word[id], prob) for id, prob in zip(indices, probs)]

def format_topics(topics, linesep="\n", tokensep="\t"):
	# type: (iterable[List[Tuple[str, float]]], ) -> str

	buffer = []

	for terms in topics:
		buffer.append(tokensep.join("({},{})".format(term, prob) for term, prob in terms))

	return linesep.join(buffer)

class LDADocument(object):

	def __init__(self, words):
		# type: (List[int], ) -> None

		self.words = words

	def __iter__(self):
		# type: () -> Iterator[int]

		return iter(self.words)

	def __len__(self):
		# type: () -> int

		return len(self.words)

	def __repr__(self):
		# type: () -> str

		return "LDADocument({})".format(repr(self.words))

class LDABase(object):

	def __init__(self):
		# type: () -> None

		np.seterr(all="raise")

	def init_topic(self):
		# type: () -> int

		return np.random.randint(self.K)

	def add_counts(self, m, t, k):
		# type: (int, int, int) -> None

		self.nmk[m, k] += 1
		self.nkt[k, t] += 1
		self.nk[k] += 1

	def sub_counts(self, m, t, k):
		# type: (int, int, int) -> None

		self.nmk[m, k] -= 1
		self.nkt[k, t] -= 1
		self.nk[k] -= 1

	def _validate(self, M, K, V):
		assert M > 0, "Number of documents must be larger than zero"
		assert K > 0, "Number of topics must be larger than zero"
		assert V > 0, "Vocabulary size must be larger than zero"

		assert self.nmk.shape == (M, K)
		assert self.nm.shape == (M, )
		assert self.nkt.shape == (K, V)
		assert self.nk.shape == (K, )

		assert self.α.shape == (K, )
		assert self.β.shape == (V, )

	def _initialize_topics(self, docs, topics):
		# type: (IterableDocuments, Dict[Any, int]) -> None

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
			left = (self.nmk[m, :] + self.α) / (self.nm[m] + self.αsum) # [K]
			however, the denominator can be dropped, because it doesn't depend on `k`
			and we only care about proportionality.
			It is done so in: 'A Theoretical and Practical Implementation Tutorial
				on Topic Modeling and Gibbs Sampling'
		"""

		left = (self.nmk[m, :] + self.α) # [K]
		right = (self.nkt[:, t] + self.β[t]) / (self.nk[:] + self.βsum) # [K]
		return left * right # [K]

	def calc_probs_selected(self, m, t, k_select):
		# type: (int, int) -> float[K]

		left = (self.nmk[m, k_select] + self.α) # [K]
		right = (self.nkt[k_select, t] + self.β[t]) / (self.nk[k_select] + self.βsum) # [K]
		return left * right # [K]

	def sample(self, m, t):
		# type: (int, int) -> int

		probs = self.calc_probs(m, t) # [K]
		return categorical(normalize(probs))

	def sample_selected(self, m, t, k_select):
		# type: (int, int, Any) -> int

		raise NotImplementedError

	def _sample_all(self, docs, topics):
		# type: (IterableDocuments, Dict[Any, int]) -> None

		from ferutility.utils import progress

		for m, doc in enumerate(progress(docs, file=stderr)):
			for i, t in enumerate(doc):
				k = topics[m, i]
				self.sub_counts(m, t, k)
				k = topics[m, i] = self.sample(m, t, k) # sample new topics
				self.add_counts(m, t, k)

	def initialize(self):
		# type: () -> None

		""" Set parameters based on input docs """

		raise NotImplementedError

	def initialize_topics(self): # step1
		# type: () -> None

		""" Initialize topics matrix """

		raise NotImplementedError

	def sample_all(self): # step2 and step3
		# type: () -> None

		""" Sample new topics """

		raise NotImplementedError

	def metric(self):
		# type: () -> float

		raise NotImplementedError

	def fit(self, n_iter=100, verbose=False):
		# type: (int, bool) -> None

		""" Fit LDA """

		assert self.docs

		self.initialize()
		self.initialize_docs()
		self.initialize_topics()
		for i in range(n_iter):
			self.sample_all()
			if verbose:
				print("Step #{}, metric: {}".format(i, self.metric()))

	def theta(self):
		# type: () -> float[M, K]

		num = self.nmk + self.α # [M, K]
		denom = self.nm + self.αsum # [M]
		return num / denom[:,None] # [M, K]

	def phi(self):
		# type: () -> float[K, V]

		num = self.nkt + self.β # [K, V]
		denom = self.nk + self.βsum # [K]
		return num / denom[:,None] # [K, V]

	def _perplexity(self, docs):
		# type: (IterableDocuments, ) -> float

		θ = self.theta()
		φ = self.phi()

		num = 0
		denom = 0

		for m, doc in enumerate(docs):
			for i, t in enumerate(doc):
				num += np.log(np.inner(φ[:,t], θ[m]))
			denom += len(doc)

		return exp(-num / denom)

	def docs2topics(self):
		# type: () -> int[M]

		return np.argmax(self.theta(), axis=-1) # [M]

	def print_topics(self, num_words=10):
		# type: (int, ) -> List[list[Tuple[str, float]]]

		topics = top_topics(self.id2word, self.phi(), num_words)
		print(format_topics(topics))

	@staticmethod
	def generate(theta, phi, doc_lens):
		# type: (float[K, V], float[M, K], Iterable[int]) -> Tuple[dict, dict]

		z = {} # sparse
		w = {} # sparse

		for m, length in enumerate(doc_lens):
			for i in range(length):
				k = z[(m, i)] = categorical(theta[m]) # scalar # doc to topic
				w[(m, i)] = categorical(phi[k]) # scalar # topic to word

		return z, w

	def inferencer(self):
		# type: () -> LDAInfer

		return cast(self, LDAInfer)

class LDA(LDABase):

	""" LDA using collapsed Gibbs sampling
		Based on:
		- https://en.wikipedia.org/wiki/Latent_Dirichlet_allocation
		- Latent Dirichlet Allocation (2003)
		- A Theoretical and Practical Implementation Tutorial on Topic Modeling and Gibbs Sampling (2011)
		- Integrating Out Multinomial Parameters in Latent Dirichlet Allocation and Naive Bayes for Collapsed Gibbs Sampling (2010)
	"""

	def __init__(self, n_topics, alpha=1., beta=1.):
		# type: (int, int, float, float) -> None

		LDABase.__init__(self)

		self.K = n_topics # number of topics

		self.alpha = alpha
		self.beta = beta

		self.word_encoder = BatchLabelEncoder(tokenizer="nltk")
		self.docs = [] # type: List[LDADocument]

		self.inttype = np.int32

	def initialize(self):
		# type: () -> None

		self.V = self.word_encoder.num_labels

		self.α = np.full(self.K, self.alpha / self.K) # [K] symmetric Dirichlet prior for document-topic distribution θ
		self.β = np.full(self.V, self.beta / self.V) # [V] symmetric Dirichlet prior for topic-word distribution φ

		self.αsum = np.sum(self.α)
		self.βsum = np.sum(self.β)

		self.nkt = np.zeros((self.K, self.V), dtype=self.inttype) # [K, V] topic-word counts
		self.nk = np.zeros((self.K, ), dtype=self.inttype) # [K] total topic counts

	def initialize_docs(self):
		# type: () -> None

		self.M = len(self.docs)

		self.nmk = np.zeros((self.M, self.K), dtype=self.inttype) # [M, K] document-topic counts
		self.nm = np.array(list(map(len, self.docs)), dtype=self.inttype) # [M] total document counts, not necessary for sampling, but useful for theta and phi calculation

		self.topics = {} # `z`, sparse document-word topics matrix (because rows can have different lengths)

	def initialize_topics(self):
		# type: () -> None

		self._validate(self.M, self.K, self.V)

		return self._initialize_topics(self.docs, self.topics)

	def sample_all(self):
		# type: () -> None

		return self._sample_all(self.docs, self.topics)

	def metric(self):
		# type: () -> float

		return self._perplexity(self.docs)

	def perplexity(self, docs):
		# type: (Iterable[List[int]], ) -> float

		return self._perplexity(docs)

	def transform(self, doc_lens):
		# type: (Iterable[int], ) -> Tuple[dict, dict]

		return self.generate(self.theta(), self.phi(), doc_lens)

	def add_doc(self, doc):
		# type: (str, ) -> int

		assert isinstance(doc, str)

		words = list(self.word_encoder.fit_transform(doc))

		ret = len(self.docs)
		self.docs.append(LDADocument(words))
		return ret

	def make_doc(self, doc):
		# type: (str, ) -> LDADocument

		assert isinstance(doc, str)

		words = list(self.word_encoder.transform(doc))
		return LDADocument(words)

class LDATermWeight(LDABase):

	""" LDA with term weighting
		Based on: "Term Weighting Schemes for Latent Dirichlet Allocation" (2010)

		Further analysis papers:
			- "Pulling Out the Stops: Rethinking Stopword Removal for Topic Models" (2017)
			- "Assessing topic model relevance: Evaluation and informative priors" (2019)
	"""

	def __init__(self, n_topics, tws="PMI", alpha=1., beta=1.):
		# type: (int, int, str, float, float) -> None

		""" tws: Term weighting scheme
			ONE: Consider every term equal (same as standard LDA)
			TF: Term frequency
			IDF: Inverse Document Frequency term weighting.
				Thus, a term occurring at almost every document has very low weighting and a term occurring at a few document has high weighting.
			PMI: Pointwise Mutual Information term weighting (default)
		"""

		LDABase.__init__(self)

		self.K = n_topics # number of topics

		self.alpha = alpha
		self.beta = beta

		self.word_encoder = BatchLabelEncoder(tokenizer="nltk")
		self.docs = [] # type: List[LDADocument]

		self.create_term_weights = {
			"ONE": self._one,
			"TF": self._tf,
			"IDF": self._idf,
			"TFIDF": self._tfidf,
			"PMI": self._pmi,
			"RAND": self._rand,
		}[tws]

		self.floattype = np.float32
		self.inttype = np.int32

	def _one(self, docs):
		# type: (Any, ) -> int[M, V]

		# return np.ones((self.M, self.V))
		return np.broadcast_to(1, (self.M, self.V)) # is this slower for indexing later?

	def _tf(self, docs):
		# type: (IterableDocuments, ) -> float[M, V]

		all_counts = Counter(chain.from_iterable(docs))
		num_counts = sum(all_counts.values())

		tw = np.array([all_counts[t] for t in range(self.V)], dtype=self.floattype) # [V]
		tw = -np.log2(tw / num_counts)

		return np.broadcast_to(tw, (self.M, self.V))

	def _idf(self, docs):
		# type: (IterableDocuments, ) -> float[M, V]

		tw = np.zeros((self.V, ), dtype=self.floattype) # [V]

		for doc in docs:
			for token in set(doc):
				tw[token] += 1

		tw = np.log2(self.M / tw)

		return np.broadcast_to(tw, (self.M, self.V))

	def _tfidf(self, docs):
		raise NotImplementedError

	def _pmi(self, docs):
		# type: (IterableDocuments, ) -> float[M, V]

		tw = np.zeros((self.M, self.V), dtype=self.floattype) # [M, V] term weights

		all_counts = Counter(chain.from_iterable(docs))

		for m, doc in enumerate(docs):
			doc_counts = Counter(doc)
			for i, t in enumerate(doc):
				tw[m, t] = -log2(doc_counts[t] / all_counts[t])

		np.clip(tw, 0, None, out=tw)
		return tw

	def _rand(self, docs):
		# type: (Any, ) -> float[M, V]

		return np.random.uniform(0, 1, (self.M, self.V)).astype(np.float32)

	def initialize(self):
		# type: () -> None

		self.V = self.word_encoder.num_labels

		self.α = np.full(self.K, self.alpha / self.K) # [K] symmetric Dirichlet prior for document-topic distribution θ
		self.β = np.full(self.V, self.beta / self.V) # [V] symmetric Dirichlet prior for topic-word distribution φ

		self.αsum = np.sum(self.α)
		self.βsum = np.sum(self.β)

		self.nkt = np.zeros((self.K, self.V), dtype=self.inttype) # [K, V] counts, same as np.sum(nmkt, axis=0)
		self.nk = np.zeros((self.K, ), dtype=self.inttype) # [K] counts, same as np.sum(nkt, axis=-1) # [K]

		#self.wkt = np.zeros((self.K, self.V), dtype=self.floattype) # [K, T] weights
		#self.wk = np.zeros((self.K, ), dtype=self.floattype) # [K] weights

	def initialize_docs(self):
		# type: () -> None

		self.M = len(self.docs)

		self.tw = self.create_term_weights(self.docs)
		print(self.tw.shape)
		print(self.tw)

		self.nmk = np.zeros((self.M, self.K), dtype=self.inttype) # [M, K] counts, same as np.sum(nmkt, axis=-1)
		self.nm = np.array(list(map(len, self.docs)), dtype=self.inttype) # [M] total document counts, not necessary for sampling, but useful for theta and phi calculation

		"""
			`wmk[m]` is same as `np.sum(wmkt[m], axis=-1)` is same as
			`np.sum(self.tw[m, :][None, :] * nmkt[m], axis=-1)`

			with
				`wmkt = np.zeros((self.M, self.K, self.V), dtype=self.floattype)` # [M, K, V] weights
				`nmkt = np.zeros((self.M, self.K, self.V), dtype=self.inttype)` # [M, K, V] counts
		"""
		#self.nmkt = np.zeros((self.M, self.K, self.V), dtype=self.inttype)
		self.wmk = np.zeros((self.M, self.K), dtype=self.floattype) # [M, K] weights, same as np.sum(nmkt, axis=-1)

		self.topics = VariableRowMatrix() # [M, Variable] `z`, sparse document-word topics matrix

	def initialize_topics(self):
		# type: () -> None

		# self._validate(self.M, self.K, self.V)

		self._initialize_topics(self.docs, self.topics)

	def calc_probs(self, m, t):
		# type: (int, int) -> float[K]

		# here using global weights works
		#wmk = np.sum(self.tw[m, :][None, :] * self.nmkt[m], axis=-1, dtype=self.floattype)
		#if not np.allclose(self.wmk[m], wmk, atol=1e-06): # after some time it still diverges because of nummerical issues
		#	raise RuntimeError("inconsistent wmk")

		# here it doesn't...
		wkt = self.tw[m, t] * self.nkt[:, t]
		#if not np.allclose(self.wkt[:, t], wkt[:]):
		#	raise RuntimeError("inconsistent wkt")

		# here it doesn't also...
		wk = np.sum(self.tw[m, :][None, :] * self.nkt, axis=-1) # not the same as `self.wk[k] (+|-)= self.tw[m, t]`
		#if not np.allclose(self.wk, wk):
		#	raise RuntimeError("inconsistent wk")

		# nk: ld.numByTopic[tid]
		# nkt: ld.numByTopicWord[tid, vid]

		left = (self.wmk[m] + self.α) # [K]
		right = (wkt[:] + self.β[t]) / (wk[:] + self.βsum) # [K]
		return left * right # [K]

	"""
	def addWordToINC(docId, tid, vid):

		# paper W*beta term in eq. 6 (https://www.aclweb.org/anthology/N10-1070.pdf)
		ld.numByTopicWordCOUNTS[tid, vid] += 1
		Nk = np.sum(docs[docId].wordWeights[None,:] * ld.numByTopicWordCOUNTS, axis=-1) # [None,:] needed for correct broadcasting. summed over words, K size array remains
		# or the above in plain python
		Nk = [sum(docs[docId].wordWeights[word_id] * ld.numByTopicWordCOUNTS[tid, word_id]
			for word_id in docs[docid].words)
				for tid in range(K)] # K size array

		# addWordTo INC
		ld.numByTopic[tid] += docs[docId].wordWeights[pid] # ld.numByTopic is a K size array

		# now both weight sums should be the same AT ALL TIMES
		assert Nk == ld.numByTopic # elementwise comparison

		# but they are not after the first document, if the weights depend on the document
	"""

	def add_counts(self, m, t, k):
		# type: (int, int, int) -> None

		self.nmk[m, k] += 1
		self.nkt[k, t] += 1
		self.nk[k] += 1

		#self.nmkt[m, k, t] += 1
		self.wmk[m, k] += self.tw[m, t]
		#self.wkt[k, t] += self.tw[m, t]
		#self.wk[k] += self.tw[m, t]

		"""
		print("docId={}, vid={}, tid={}".format(m, t, k))

		wk = np.sum(self.tw[m, :][None, :] * self.nkt, axis=-1)
		print("ld.numByTopicWordCOUNTS:\n", self.nkt)
		print("paper sum:", wk)
		print("ld.numByTopic:", self.wk)

		if not np.allclose(wk, self.wk):
			raise RuntimeError("not equal")
		"""

	def sub_counts(self, m, t, k):
		# type: (int, int, int) -> None

		self.nmk[m, k] -= 1
		self.nkt[k, t] -= 1
		self.nk[k] -= 1

		#self.nmkt[m, k, t] -= 1
		self.wmk[m, k] -= self.tw[m, t]
		#self.wkt[k, t] -= self.tw[m, t]
		#self.wk[k] -= self.tw[m, t]

	def sample_all(self):
		# type: () -> None

		self._sample_all(self.docs, self.topics)

	def metric(self):
		# type: () -> float

		return self._perplexity(self.docs)

class LDAInfer(LDA):

	def __init__(self):
		# type: () -> None

		self.nkt_old = self.nkt
		self.nk_old = self.nk
		self.docs = []

	def calc_probs(self, m, t):
		# type: (int, int) -> float[]

		left = (self.nmk[m, :] + self.α) # [K]
		right = (self.nkt[:, t] + self.nkt_old[:, t] + self.β) / (self.nk[:] + self.nk_old[:] + self.βsum) # [K]

		return left * right # [K]

	def initialize(self):
		# type: () -> None

		self.nkt = np.zeros((self.K, self.V), dtype=self.inttype)
		self.nk = np.zeros((self.K, ), dtype=self.inttype)

	def initialize_docs(self):
		# type: () -> None

		self.M = len(self.docs)

		self.nmk = np.zeros((self.M, self.K), dtype=self.inttype)
		self.nm = np.array(list(map(len, self.docs)), dtype=self.inttype)

		self.topics = {} # `z`, sparse document-word topics matrix (because rows can have different lengths)

if __name__ == "__main__":
	from sklearn.datasets import fetch_20newsgroups
	from .pickle import cache

	ng = fetch_20newsgroups()

	@cache("lda.init.p.gz")
	def init_lda():
		lda = LDA(n_topics=20)

		for doc in ng.data:
			lda.add_doc(doc)

		return lda

	@cache("lda_tw.init.p.gz")
	def init_lda_tw():
		lda = LDATermWeight(n_topics=20)

		for doc in ng.data:
			lda.add_doc(doc)

		return lda

	debug_docs = [
		[0, 6, 3, 9, 1, 5],
		[9, 8, 8, 7, 1, 0],
		[2, 4, 4, 5, 0, 1],
	]

	print("LDA")
	lda = LDATermWeight(2, tws="RAND")
	lda.add_docs_encoded()
	lda.fit(10, docs=debug_docs, verbose=True)
	lda.print_topics()

	print("LDA")
	lda = init_lda()
	lda.fit(10, verbose=True)

	print("LDATermWeight")
	lda_tw = init_lda_tw()
	lda.fit(2, verbose=True)
