from __future__ import absolute_import, division, print_function, unicode_literals

from builtins import range

from random import choice, randrange
from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from typing import Iterator, Tuple

def randstr(length, charset):
	# type: (int, str) -> str

	""" Returns a (noncryptographic) random string consisting of characters from `charset`
		of length `length`.
	"""

	return "".join(choice(charset) for i in range(length))  # nosec

def randbytes(size):
	# type: (int, ) -> bytes

	""" Returns (noncryptographic) random bytes of length `length`.
	"""

	return b"".join(chr(randrange(0, 256)) for _ in range(size))  # nosec

def rgb_colors():
	# type: () -> Iterator[Tuple[int, int, int]]

	""" Yields a stream of (noncryptographic) random RGB color tuples.
	"""

	while True:
		rgb = randrange(0, 256**3)  # nosec
		rg, b = divmod(rgb, 256)
		r, g = divmod(rg, 256)
		yield (r, g, b)
