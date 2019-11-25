from __future__ import absolute_import, division, print_function, unicode_literals

from future.utils import viewkeys, viewitems
from builtins import sum

from itertools import islice
from typing import TYPE_CHECKING

from .file import PathOrTextIO

if TYPE_CHECKING:
	from typing import Dict, TextIO, Union, Iterator, List
	from .gensim import KeyedVectors

from nltk.tokenize import word_tokenize as tokenize

def gensim_indexer(embeddings, doc, ignore=True):
	# type: (KeyedVectors, str) -> Iterator[int]

	for word in tokenize(doc):
		try:
			yield embeddings.vocab[word.lower()].index
		except KeyError:
			if ignore:
				pass
			else:
				raise

def batch_gensim_indexer(embeddings, docs, ignore=True):
	# type: (KeyedVectors, Iterable[str]) -> Iterator[List[int]]

	for doc in docs:
		yield list(gensim_indexer(embeddings, doc, ignore))

def load_freqs(fname, normalize=False, limit=None):
	# type: (Union[str, TextIO], ) -> Dict[str, int]

	with PathOrTextIO(fname, "rt", encoding="utf-8") as fin:
		freqs = dict()

		for line in islice(fin, limit):
			word, count = line.split()
			freqs[word] = int(count)

	if normalize:
		total = sum(viewkeys(freqs))

		for word, count in viewitems(freqs):
			freqs[word] = count / total

	return freqs
