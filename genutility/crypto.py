from __future__ import generator_stop

from itertools import cycle
from typing import Iterable, Iterator


def xor_stream(it, key, cyclekey=True):
	# type: (Iterable[bytes], Iterable[bytes], bool) -> Iterator[bytes]

	if cyclekey:
		key = cycle(key)

	for i, j in zip(it, key):
		yield bytes([i ^ j])
