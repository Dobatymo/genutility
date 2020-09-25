from __future__ import absolute_import, division, print_function, unicode_literals

from builtins import map, range

from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from typing import Iterator, Tuple

def obj2tuple(obj):
	return (obj, )

def row_indices(n, square_length):
	""" Returns the one-dimensional indices of all the cells belonging to the
		same row as index `n`.
	"""

	j = n // square_length
	return range(j * square_length, (j + 1) * square_length)

def col_indices(n, square_length):
	""" Returns the one-dimensional indices of all the cells belonging to the
		same column as index `n`.
	"""

	j = n % square_length
	return range(j, square_length * (square_length - 1) + j + 1, square_length)

def subblock_indices(n, outer_square_length, inner_square_length):
	# type: (int, int, int) -> Iterator[Tuple[int, int]]

	""" Returns the one-dimensional indices of all the cells belonging to the
		same block as index `n`.
		`outer_square_length` is the number of cells per block.
		`inner_square_length` current has to be sqrt(block_size).
	"""

	i = outer_square_length
	j = inner_square_length

	if n >= i * i:
		raise ValueError("n not contained in matrix")

	if j * j != i:
		raise ValueError("Currently only squares are supported")

	x, y = (n % i // j, n // i // j)

	for iy in range(j):
		for ix in range(j):
			yield (y * i * j) + (i * iy) + (x * j) + (ix)

def triangular_indices(n):

	""" Returns all combinations of indices for a sequence of length `n` with duplicates and self-combinations.
		triangular_indices(4) -> (0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)
	"""

	for i in range(n-1):
		for j in range(i+1, n):
			yield i, j

def to_2d_index(n, width):
	return n // width, n % width

def indices_2d(n, width):
	# type: (int, int) -> Iterator[Tuple[int, int]]

	for i in range(n):
		yield i // width, i % width

def window_combinations_indices(size, window_size):
	# type: (int, int) -> Iterator[Tuple[int, int]]

	""" Yields all pairs of indices of a sequence of length `size` which are within a window
		of size `window_size`.

		Example:
			window_combinations_indices(3, 2) -> (0, 1), (1, 2)
			window_combinations_indices(4, 3) -> (0, 1), (0, 2), (1, 2), (1, 3), (2, 3)
	"""

	if window_size > size:
		raise ValueError("window size cannot exceed size")

	for a in range(0, size - 1):
		end = min(a + window_size, size)
		for b in range(a+1, end):
			yield a, b

def _combination_indices(start, sizes):

	""" earlier (left) dimensions can never be higher than later (right) dimensions. """

	if len(sizes) > 1:
		for i in range(start, sizes[0]):
			for j in _combination_indices(i, sizes[1:]):
				yield (i, ) + j
	else:
		for i in map(obj2tuple, range(start, sizes[0])):
			yield i

def combination_indices(*sizes):

	""" Given sequences of size a, b, c, ... yield the indices to index into each of them,
		so that all combinations of elements from the sequences are returned.
	"""

	return _combination_indices(0, sizes)
