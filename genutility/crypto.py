from __future__ import absolute_import, division, print_function, unicode_literals

from builtins import bytes, zip

from itertools import cycle
from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from typing import Iterable, Iterator

def xor_stream(it, key, cyclekey=True):
	# type: (Iterable[bytes], Iterable[bytes], bool) -> Iterator[bytes]

	if cyclekey:
		key = cycle(key)

	for i, j in zip(it, key):
		yield bytes([i ^ j])
