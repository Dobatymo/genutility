from __future__ import absolute_import, division, print_function, unicode_literals

from itertools import islice
from typing import TYPE_CHECKING

import numpy as np
from gensim.models.keyedvectors import KeyedVectors as KeyedVectorsOriginal
from gensim.models.keyedvectors import Vocab

from .file import PathOrTextIO

if TYPE_CHECKING:
	from typing import Callable, Collection, Iterator, Optional, TextIO, Tuple, Union

class DuplicateEntry(ValueError):
	pass

class KeyedVectors(KeyedVectorsOriginal):

	""" Enhancement of the original `gensim` `KeyedVectors` class. Supports loading of `glove` and
		`muse` word vector files.
	"""

	@classmethod
	def load_a_format(cls, fin, vocab_size, vector_size, datatype=np.float32, discard=None):
		# type: (TextIO, int, int, Optional[Callable[[str], bool]]) -> KeyedVectorsOriginal

		if discard is None:
			discard = lambda x: False

		result = cls(vector_size)
		result.vector_size = vector_size
		result.vectors = np.zeros((vocab_size, vector_size), dtype=datatype)

		for line in fin:
			word, vect = line.rstrip().split(" ", 1)

			if discard(word):
				continue

			weights = np.fromstring(vect, sep=" ", dtype=np.float32)
			# raise ValueError("invalid vector on line %s; is vector_size incorrect or file otherwise damaged?" % (i+1,))

			if word in result.vocab:
				raise DuplicateEntry(word)

			word_id = len(result.index2word)
			result.vocab[word] = Vocab(index=word_id, count=vocab_size - word_id)
			result.vectors[word_id] = weights
			result.index2word.append(word)

		real_size = len(result.index2word)

		if real_size != vocab_size:
			if discard is None:
				raise EOFError("unexpected end of input; is vocab_size incorrect or file otherwise damaged?")
			else:
				result.vectors.resize((real_size, vector_size)) # this should be no-copy

		return result

	def add(self, wwc):
		# type: (Collection[Tuple[str, np.ndarray, int]], ) -> None

		""" `wwc` is a collection of (word, weights, count) tuples """

		vocab_size, vector_size = self.vectors.shape
		self.vectors.resize((vocab_size + len(wwc), vector_size))
		for i, (word, weights, count) in enumerate(wwc):
			word_id = vocab_size + i
			voc = Vocab(index=word_id, count=count)
			self.vocab[word] = voc
			self.vectors[word_id] = weights
			self.index2word.append(word)
			yield voc

	def add_word(self, word, weights=None, count=1):
		if not weights:
			vocab_size, vector_size = self.vectors.shape
			weights = np.random.randn(1, vector_size)

		return list(self.add([(word, weights, count)]))[0]

	@classmethod
	def load_muse_format(cls, fname, limit=None, discard=None):
		# type: (Union[str, TextIO], int, Optional[Callable[[str], bool]]) -> KeyedVectorsOriginal

		""" reads at most `limit` vectors from muse file, if `discard` is not None it might be less.
			discard is a callable which should return False if word should not be loaded from file.
		"""

		with PathOrTextIO(fname, "rt", encoding="utf-8", newline="\n") as fin:
			vocab_size_, vector_size = map(int, next(fin).split(" "))
			if limit:
				vs = min(vocab_size_, limit)
			else:
				vs = vocab_size_

			try:
				return cls.load_a_format(islice(fin, limit), vs, vector_size, discard=discard)
			except DuplicateEntry as e:
				raise ValueError("duplicate word '{}' in {}".format(e, fname))

	@classmethod
	def load_glove_format(cls, fname, limit, vector_size, discard=None):
		# type: (Union[str, TextIO], int, int, Optional[Callable[[str], bool]]) -> KeyedVectorsOriginal

		""" Reads at most `limit` vectors from glove file, if `discard` is not None it might be less.
			`discard` is a callable which should return False if word should not be loaded from file.
		"""

		with PathOrTextIO(fname, "rt", encoding="utf-8") as fin:
			try:
				return cls.load_a_format(islice(fin, limit), limit, vector_size, discard=discard)
			except DuplicateEntry as e:
				raise ValueError("duplicate word '{}' in {}".format(e, fname))

	def get_keras_embedding(self, train_embeddings=False, mask_zero=True):
		try:
			from keras.layers import Embedding
		except ImportError:
			raise ImportError("Please install Keras to use this function")

		if mask_zero == True:
			self.index2word = [None]+ self.index2word
			zero_vec = np.zeros((1, self.vector_size))
			self.vectors = np.concatenate([zero_vec, self.vectors], axis=0)

		weights = self.vectors

		# set `trainable` as `False` to use the pretrained word embedding
		# No extra mem usage here as `Embedding` layer doesn't create any new matrix for weights
		layer = Embedding(
			input_dim=weights.shape[0], output_dim=weights.shape[1],
			weights=[weights], trainable=train_embeddings, mask_zero=mask_zero
		)
		return layer

	def transform_words_to_indices(self, words):
		# type: (Collection[str], ) -> Iterator[int]

		return (self.vocab[word].index for word in words)

	def transform_words_to_indices_tuple(self, words):
		# type: (Collection[str], ) -> Tuple[int, ...]

		return tuple(self.transform_words_to_indices(words))

if __name__ == "__main__":

	import argparse
	parser = argparse.ArgumentParser()
	parser.add_argument("glove_file")
	parser.add_argument("muse_file")
	args = parser.parse_args()

	word_vectors = KeyedVectors.load_glove_format(args.glove_file, 400000, 300)
	print(word_vectors.most_similar(positive=['woman', 'king'], negative=['man']))
	word_vectors = KeyedVectors.load_muse_format(args.muse_file)
	print(word_vectors.most_similar(positive=['woman', 'king'], negative=['man']))
