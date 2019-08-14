from __future__ import absolute_import, division, print_function, unicode_literals

from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from typing import MutableSequence, Callable

from past.builtins import cmp

def _insertion(seq, cmp_, left, right, gap):
	# type: (MutableSequence, Callable, int, int, int)

	# print("_insertion", left, right, gap)

	loc = left+gap
	while loc <= right:
		i = loc - gap
		value = seq[loc]
		while i >= left and cmp_(seq[i], value) > 0:
			seq[i+gap] = seq[i]
			i -= gap
		seq[i+gap] = value
		loc += gap

GROUP_SIZE = 5

def median_of_medians(seq, cmp_=None, left=None, right=None, gap=1):
	# type: (MutableSequence, Callable, int, int, int)

	""" Approximate median selection algorithm. """

	cmp_ = cmp_ or cmp

	if not left:
		left = 0
	if not right:
		right = len(seq) - 1

	span = GROUP_SIZE*gap
	num = (right - left + 1) // span

	# print("median_of_medians", left, right, gap, span, num)

	if num == 0:
		_insertion(seq, cmp_, left, right, gap)
		num = (right - left + 1) // gap
		return left + gap*(num-1) // 2

	s = left
	while s < right-span:
		_insertion(seq, cmp_, s, s + span - 1, gap)
		s += span

	if num < GROUP_SIZE:
		_insertion(seq, cmp_, left+span // 2, right, span)
		return left + num*span // 2
	else:
		return median_of_medians(seq, cmp_, left + span // 2, s-1, span)
