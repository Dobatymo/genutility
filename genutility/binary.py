from __future__ import absolute_import, division, print_function, unicode_literals

from builtins import range
from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from typing import Iterable, Iterator

def encode_binary(boolit, pad='0'):
	# type: (Iterable[bool], ) -> bytes

	bin = "".join('1' if b else '0' for b in boolit)
	bin += pad*(8 - len(bin)%8) # pad
	assert len(bin) % 8 == 0
	return bytes(int(bin[x:x+8], 2) for x in range(0, len(bin), 8))

def decode_binary(key):
	# type: (bytes, ) -> Iterator[bool]

	for b in key:
		for c in "{:08b}".format(b):
			yield True if c == '1' else False
