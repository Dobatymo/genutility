from __future__ import absolute_import, division, print_function, unicode_literals

import numpy as np

def hamming_distance(a, b):
	# type: (bytes, bytes) -> int

	a = np.unpackbits(np.frombuffer(a, dtype=np.uint8))
	b = np.unpackbits(np.frombuffer(b, dtype=np.uint8))
	return np.count_nonzero(a != b)
