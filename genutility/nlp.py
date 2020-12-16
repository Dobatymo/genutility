from __future__ import generator_stop

from itertools import islice
from typing import TYPE_CHECKING

from nltk.tokenize import word_tokenize as tokenize

from .file import PathOrTextIO

if TYPE_CHECKING:
	from typing import Dict, Iterable, Iterator, List, Optional, TextIO, Union

	from .gensim import KeyedVectors

def gensim_indexer(embeddings, doc, ignore=True):
	# type: (KeyedVectors, str, bool) -> Iterator[int]

	for word in tokenize(doc):
		try:
			yield embeddings.vocab[word.lower()].index
		except KeyError:
			if ignore:
				pass
			else:
				raise

def batch_gensim_indexer(embeddings, docs, ignore=True):
	# type: (KeyedVectors, Iterable[str], bool) -> Iterator[List[int]]

	for doc in docs:
		yield list(gensim_indexer(embeddings, doc, ignore))

def load_freqs(fname, normalize=False, limit=None):
	# type: (Union[str, TextIO], bool, Optional[int]) -> Dict[str, int]

	with PathOrTextIO(fname, "rt", encoding="utf-8") as fin:
		freqs = dict()

		for line in islice(fin, limit):
			word, count = line.split()
			freqs[word] = int(count)

	if normalize:
		total = sum(freqs.keys())

		for word, count in freqs.items():
			freqs[word] = count / total

	return freqs
