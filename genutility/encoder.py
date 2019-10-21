from __future__ import absolute_import, division, print_function, unicode_literals

from builtins import map

from itertools import chain

import numpy as np
from sklearn.preprocessing import LabelEncoder
from nltk.tokenize import word_tokenize

from .func import identity

class BatchLabelEncoder(object):

	""" Similar to `sklearn.preprocessing.LabelEncoder` but accepts a list of sentences as inputs
		and returns a list of lists of integer labels.
		Warning: Calling `fit` doesn't reset the encoder. To do so call `reset()` explicitly.
		cf. `keras_preprocessing.text.Tokenizer`
	"""

	def __init__(self, tokenizer):
		# type: (str, ) -> None

		self.tokenizer = {
			"none": identity,
			"nltk": word_tokenize,
		}[tokenizer]
		self.reset()

	def reset(self):
		# type: () -> None

		""" Initializes all mappings with empty containers. """

		self.token2idx = {} # type: Dict[Any, int]
		self.idx2count = []
		self.idx2token = []

	def finalize(self, vocab_size):
		# type: (int, ) -> None

		""" This only keeps the most frequent `vocab_size` words in the vocabulary.
			This will change the assigned indices, so if `transform` was used before `finalize`,
			they cannot be transformed back using `inverse_transform`.
		"""

		self.idx2count = np.array(self.idx2count)
		self.idx2token = np.array(self.idx2token)
		indices = np.argsort(-self.idx2count)[:vocab_size]

		self.idx2count = self.idx2count[indices]
		self.idx2token = self.idx2token[indices]

		self.token2idx = {token: i for i, token in enumerate(self.idx2token)}

	def partial_fit_single(self, token):
		# type: (T, ) -> int

		vocab_size = self.num_labels
		idx = self.token2idx.setdefault(token, vocab_size)
		if idx == vocab_size: # inserted new token
			self.idx2count.append(1)
			self.idx2token.append(token)
		else:
			self.idx2count[idx] += 1

		return idx

	def partial_fit(self, sentence):
		# type: (str, ) -> None

		for token in self.tokenizer(sentence):
			self.partial_fit_single(token)

	def partial_fit_batch(self, sentences):
		# type: (Iterable[str], ) -> None

		for sentence in sentences:
			self.partial_fit(sentence)

	def fit_single(self, token):
		# type: (str, ) -> None

		self.partial_fit_single(token)

	def fit(self, sentence):
		# type: (str, ) -> None

		self.partial_fit(sentence)

	def fit_batch(self, sentences):
		# type: (Iterable[str], ) -> None

		self.partial_fit_batch(sentences)

	def transform_single(self, token):
		# type: (Iterable[str], ) -> Iterator[List[int]]

		""" Unknown labels are skipped. """

		return self.token2idx[token]

	def transform(self, sentence, ignore=True):
		# type: (str, ) -> Iterator[int]

		for token in self.tokenizer(sentence):
			try:
				yield self.transform_single(token)
			except KeyError:
				if ignore:
					pass
				else:
					raise

	def transform_batch(self, sentences, ignore=True):
		# type: (Iterable[str], ) -> Iterator[List[int]]

		""" Unknown labels are skipped. """

		for sentence in sentences:
			yield list(self.transform(sentence, ignore))

	def fit_transform_single(self, token):
		# type: (Iterable[str], ) -> Iterator[List[int]]

		return self.partial_fit_single(token)

	def fit_transform(self, sentences):
		# type: (str, ) -> Iterator[int]

		self.partial_fit(sentences)
		return self.transform(sentences)

	def fit_transform_batch(self, sentences):
		# type: (Iterable[str], ) -> Iterator[List[int]]

		self.partial_fit_batch(sentences)
		return self.transform_batch(sentences)

	def inverse_transform_single(self, idx):
		# type: (int, ) -> str

		return self.idx2token[idx]

	def inverse_transform(self, indices):
		# type: (Iterable[int], ) -> Iterator[str]

		for idx in indices:
			yield self.inverse_transform_single(idx)

	def inverse_transform_batch(self, list_of_indices):
		# type: (Iterable[Iterable[int]], ) -> Iterator[List[str]]

		for indices in list_of_indices:
			yield list(self.inverse_transform(indices))

	@property
	def num_labels(self):
		assert len(self.token2idx) == len(self.idx2count) == len(self.idx2token)
		return len(self.idx2token)
