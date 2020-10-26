from __future__ import absolute_import, division, print_function, unicode_literals

from builtins import range

from operator import itemgetter
from typing import TYPE_CHECKING

from .func import identity
from .indexing import triangular_indices

if TYPE_CHECKING:
	from typing import Callable, Iterable, Iterator, MutableSequence, Optional, Sequence, Tuple, TypeVar

	from .typing import Comparable
	T = TypeVar("T")

class LazyStringList(object):

	def __init__(self, length):
		# type: (int, ) -> None

		self.length = length

	def __getitem__(self, idx):
		# type: (int, ) -> str

		return str(idx)

	def __len__(self):
		# type: () -> int

		return self.length

	def __iter__(self):
		# type: () -> Iterator[str]

		return map(str, range(self.length))

	def __contains__(self, idx):
		# type: (int, ) -> bool

		return 0 <= idx < self.length

def pop_many(seq, func):
	# type: (MutableSequence[T], Callable) -> Iterator[T]

	""" `pop()`s values from `seq` where func(value) is true.
		For performance reasons the elements are popped
		and yielded in reverse order.
	"""

	idx = [i for i, elm in enumerate(seq) if func(elm)]

	for i in reversed(idx):
		yield seq.pop(i)

def triangular(seq):
	# type: (Sequence[T], ) -> Iterator[Tuple[T, T]]

	""" Returns all combinations of items of `seq` with duplicates and self-combinations.
		triangular([1, 2, 3, 4]) -> (1, 2), (1, 3), (1, 4), (2, 3), (2, 4), (3, 4)
	"""

	for i, j in triangular_indices(len(seq)):
		yield seq[i], seq[j]

def sliding_window(seq, size, step=1):
	# type: (Sequence[T], int, int) -> Iterator[Sequence[T]]

	""" Similar to `iter.x_wise()` except that it returns slices of a sequence.
		sliding_window([1, 2, 3], 2) -> [1, 2], [2, 3]
		sliding_window([1, 2, 3, 4, 5], 2, 3) -> [1, 2], [4, 5]
	"""

	seqlen = len(seq)
	if size > seqlen:
		raise ValueError("size must be less or equal the length of the sequence")

	for i in range(0, seqlen-size+1, step):
		yield seq[i:i+size]

def batch(seq, size):
	# type: (Sequence[T], int) -> Iterator[Sequence[T]]

	""" Similar to `iter.batch()` except that it returns slices of a sequence.
		sliding_window([1, 2, 3], 2) -> [1, 2], [2, 3]
		sliding_window([1, 2, 3, 4, 5], 2, 3) -> [1, 2], [4, 5]
	"""

	if size < 1:
		raise ValueError("size must be larger than 0")

	seqlen = len(seq)

	for i in range(0, (seqlen + size - 1) // size):
		yield seq[i*size:(i+1)*size]

def delete_duplicates_from_sorted_sequence(seq, key=None):
	# type: (MutableSequence[T], Optional[Callable[[T], Comparable]]) -> None

	""" Deletes duplicates from a sorted sequence `seq` based on `key`.
		Works in-place.
	"""

	key = key or identity
	i = 0
	while i < len(seq) - 1:
		if key(seq[i]) == key(seq[i+1]):
			del seq[i+1]
		else:
			i += 1

remove_duplicate_rows_from_sorted_table = lambda seq, key: delete_duplicates_from_sorted_sequence(seq, itemgetter(key))

def cycle_sort(seq):
	# type: (MutableSequence[T], ) -> Iterator[Tuple[int, int]]

	""" Sort a sequence in place and yield swaps.
		based on: https://rosettacode.org/wiki/Sorting_algorithms/Cycle_sort#Python
	"""

	# Loop through the sequence to find cycles to rotate.
	for cycle_start, item in enumerate(seq):

		# Find where to put the item.
		pos = cycle_start
		for item2 in seq[cycle_start + 1:]:
			if item2 < item:
				pos += 1

		# If the item is already there, this is not a cycle.
		if pos == cycle_start:
			continue

		# Otherwise, put the item there or right after any duplicates.
		while item == seq[pos]:
			pos += 1
		seq[pos], item = item, seq[pos]
		yield cycle_start, pos

		# Rotate the rest of the cycle.
		while pos != cycle_start:

			# Find where to put the item.
			pos = cycle_start
			for item2 in seq[cycle_start + 1:]:
				if item2 < item:
					pos += 1

			# Put the item there or right after any duplicates.
			while item == seq[pos]:
				pos += 1
			seq[pos], item = item, seq[pos]
			if pos != cycle_start:
				yield cycle_start, pos
