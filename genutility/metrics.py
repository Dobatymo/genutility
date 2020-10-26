from __future__ import absolute_import, division, print_function, unicode_literals

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
	from typing import Callable, Iterable, List, Optional
	Tokenizer = Callable[[str], Iterable[str]]

def hamming_distance(a, b):
	# type: (bytes, bytes) -> int

	a = np.unpackbits(np.frombuffer(a, dtype=np.uint8))
	b = np.unpackbits(np.frombuffer(b, dtype=np.uint8))
	return np.count_nonzero(a != b)

def default_tokenizer(text):
	# type: (str, ) -> List[str]

	return text.lower().split()

def same_words_similarity(a, b, tokenizer=None):
	# type: (str, str, Optional[Tokenizer]) -> int

	tokenizer = tokenizer or default_tokenizer

	set_a = set(tokenizer(a))
	set_b = set(tokenizer(b))

	return len(set_a & set_b)
