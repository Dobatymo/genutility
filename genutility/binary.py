from __future__ import absolute_import, division, print_function, unicode_literals

from builtins import range, str
from future.utils import PY2

from typing import TYPE_CHECKING

from .exceptions import assert_choice

if TYPE_CHECKING:
	from typing import Iterable, Iterator, Union

if PY2:
	bytes = bytearray

def encode_binary(boolit, pad="0"):
	# type: (Union[str, Iterator[bool]], str) -> bytes

	""" Encode a string consisting of 0s and 1s or an iterable returns boolean values
		to bytes.

		Example:
		encode_binary("1111111100000001") -> b'\xff\x01'
		encode_binary([True]*8+[False]*7+[True]) -> b'\xff\x01'
	"""

	assert_choice("pad", pad, {"0", "1"})

	if isinstance(boolit, str):
		bin = boolit
	else:
		bin = "".join("1" if b else "0" for b in boolit)

	bin += pad * ((8 - len(bin)%8) % 8) # pad
	assert len(bin) % 8 == 0
	return bytes(int(bin[x:x+8], 2) for x in range(0, len(bin), 8))

def _str2bool_it(s):
	# type: (Iterable[str], ) -> Iterator[bool]

	for chunk in s:
		for c in chunk:
			yield True if c == "1" else False

def decode_binary(key, tostring=False):
	# type: (bytes, bool) -> Union[str, Iterator[bool]]

	""" Decode bytes to either a string of 0s and 1s or an iterable of booleans.
	"""

	it = ("{:08b}".format(b) for b in key)

	if tostring:
		return "".join(it)
	else:
		return _str2bool_it(it)
