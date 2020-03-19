from __future__ import absolute_import, division, print_function, unicode_literals

from builtins import range
from itertools import product
from operator import itemgetter
from typing import TYPE_CHECKING

from .func import identity
from .indexing import triangular_indices

if TYPE_CHECKING:
	from typing import Callable, Iterable, Iterator, MutableSequence, Tuple, Sequence

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
	# type: (Sequence[T], Callable) -> Iterator[T]

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

def sliding_window(seq, size):
	# type: (Sequence, int) -> Iterator[Sequence]

	seqlen = len(seq)
	assert size <= seqlen

	for i in range(0, seqlen-size+1):
		yield seq[i:i+size]

# was: read_x
def batch(seq, size):
	# type: (Sequence, int) -> Iterator[Sequence]

	seqlen = len(seq)

	for i in range(0, (seqlen + size - 1) // size):
		yield seq[i*size:(i+1)*size]

def merge(lists, optimize_for_speed=True):
	# type: (Iterable[Iterable], ) -> list

	""" merge lists into one, while removing duplicates but keeping element order.
		`optimize_for_speed` is True has better runtime complexity
		`optimize_for_speed` is False uses less memory
	"""

	merged = []

	if optimize_for_speed:
		uniques = set()
		for list in lists:
			for element in list:
				if element not in uniques:
					merged.append(element)
					uniques.add(element)

	else:
		for list in lists:
			for element in list:
				if element not in merged:
					merged.append(element)

	return merged

def delete_duplicates_from_sorted_sequence(seq, key=None):
	# type: (MutableSequence, Callable) -> None

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

def cycle_sort(sequence):
	# type: (MutableSequence, ) -> Iterator[Tuple[int, int]]

	""" Sort a sequence in place and yield swaps.
		based on: https://rosettacode.org/wiki/Sorting_algorithms/Cycle_sort#Python
	"""

	# Loop through the sequence to find cycles to rotate.
	for cycle_start, item in enumerate(sequence):

		# Find where to put the item.
		pos = cycle_start
		for item2 in sequence[cycle_start + 1:]:
			if item2 < item:
				pos += 1

		# If the item is already there, this is not a cycle.
		if pos == cycle_start:
			continue

		# Otherwise, put the item there or right after any duplicates.
		while item == sequence[pos]:
			pos += 1
		sequence[pos], item = item, sequence[pos]
		yield cycle_start, pos

		# Rotate the rest of the cycle.
		while pos != cycle_start:

			# Find where to put the item.
			pos = cycle_start
			for item2 in sequence[cycle_start + 1:]:
				if item2 < item:
					pos += 1

			# Put the item there or right after any duplicates.
			while item == sequence[pos]:
				pos += 1
			sequence[pos], item = item, sequence[pos]
			if pos != cycle_start:
				yield cycle_start, pos
