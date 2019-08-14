from __future__ import absolute_import, division, print_function, unicode_literals

from builtins import bytes, zip
from itertools import cycle

def xor_stream(it, key, cyclekey=True):
	# type: (Iterable[bytes], Iterable[bytes]) -> Iterator[bytes]

	if cyclekey:
		key = cycle(key)

	for i, j in zip(it, key):
		yield bytes([i ^ j])
