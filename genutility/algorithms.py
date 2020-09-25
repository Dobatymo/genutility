from __future__ import absolute_import, division, print_function, unicode_literals

from past.builtins import cmp

from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from typing import Callable, MutableSequence

def _insertion(seq, cmp_, left, right, gap):
	# type: (MutableSequence, Callable, int, int, int) -> None

	loc = left + gap
	while loc <= right:
		i = loc - gap
		value = seq[loc]
		while i >= left and cmp_(seq[i], value) > 0:
			seq[i + gap] = seq[i]
			i -= gap
		seq[i+gap] = value
		loc += gap

GROUP_SIZE = 5

def median_of_medians(seq, cmp_=None, left=0, right=None, depth=0):
	# type: (MutableSequence, Callable, int, int, int) -> int

	""" Approximate median selection algorithm.
		This is not the full median of medians algorithm.
		Currently only works for len(seq) == GROUP_SIZE ** x
	"""

	offset = (GROUP_SIZE ** (depth + 1) - GROUP_SIZE ** depth) // 2

	gap = GROUP_SIZE ** depth

	cmp_ = cmp_ or cmp

	if not right:
		right = len(seq) - 1

	span = GROUP_SIZE*gap
	num = (right - left + 1) // span

	if num == 0:
		_insertion(seq, cmp_, left, right, gap)
		num = (right - left + 1) // gap
		return left + gap * (num - 1) // 2  # select median

	s = left
	while s < right:
		_insertion(seq, cmp_, s, s + span - 1, gap)
		s += span

	if num < GROUP_SIZE:
		_insertion(seq, cmp_, left + offset, right, span)
		return left + offset + num * span // 2  # select median
	else:
		return median_of_medians(seq, cmp_, left + offset, right, depth + 1)
