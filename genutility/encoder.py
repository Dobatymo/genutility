from __future__ import absolute_import, division, print_function, unicode_literals

from builtins import map

from itertools import chain
from sklearn.preprocessing import LabelEncoder
from nltk.tokenize import word_tokenize

class BatchLabelEncoder(object):

	""" Similar to `sklearn.preprocessing.LabelEncoder` but accepts a list of sentences as inputs
		and returns a list of lists of integer labels.
		cf. `keras_preprocessing.text.Tokenizer`
	"""

	def __init__(self, tokenizer=None):
		self.tokenizer = tokenizer or word_tokenize
		self.enc = LabelEncoder()

	def fit(self, sentences):
		# type: (Iterable[str], ) -> None

		X = list(chain.from_iterable(map(self.tokenizer, sentences)))
		self.enc.fit(X)

	def transform(self, sentences):
		# type: (Iterable[str], ) -> Iterator[List[int]]

		for sent in sentences:
			yield self.enc.transform(self.tokenizer(sent))

	def fit_transform(self, sentences):
		# type: (Iterable[str], ) -> Iterator[List[int]]

		self.fit(sentences)
		return self.transform(sentences)

	@property
	def num_labels(self):
		return len(self.enc.classes_)
