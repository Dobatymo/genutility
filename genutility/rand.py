from __future__ import absolute_import, division, print_function, unicode_literals
from builtins import range

from random import choice, randrange

def randstr(length, charset):
	return "".join(choice(charset) for i in range(length))

def randbytes(size):
	return b"".join(chr(randrange(0, 256)) for _ in range(size))

def rgb_colors():
	while True:
		rgb = randrange(0, 256**3)
		rg, b = divmod(rgb, 256)
		r, g = divmod(rg, 256)
		yield (r, g, b)
