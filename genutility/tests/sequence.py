from __future__ import absolute_import, division, print_function, unicode_literals

from operator import itemgetter

from genutility.test import MyTestCase, parametrize
from genutility.func import identity
from genutility.sequence import merge, cycle_sort, delete_duplicates_from_sorted_sequence, sliding_window

class SequenceTest(MyTestCase):

	@parametrize(
		([], 0, [[]]),
		([1, 2, 3], 1, [[1], [2], [3]]),
		([1, 2, 3], 2, [[1, 2], [2, 3]]),
		([1, 2, 3], 3, [[1, 2, 3]]),
	)
	def test_sliding_window(self, input, size, truth):
		result = list(sliding_window(input, size))
		self.assertEqual(truth, result)

	@parametrize(
		([], []),
		([[1, 2], [3, 4]], [1, 2, 3, 4]),
		([[1, 2], [2, 3]], [1, 2, 3]),
		([[4, 1], [2, 3]], [4, 1, 2, 3]),
		([[4, 1], [2, 1]], [4, 1, 2]),
	)
	def test_merge(self, input, truth):
		result = merge(input)
		self.assertIterEqual(truth, result)

	@parametrize(
		([1, 2, 3], ()),
		([1, 3, 2], ((1, 2),)),
		([2, 1, 3], ((0, 1),)),
		([4, 3, 2, 1], ((0, 3), (1, 2))),
	)
	def test_cycle_sort(self, list, truth):
		result = cycle_sort(list)
		self.assertIterEqual(truth, result)

	@parametrize(
		([["asd"], ["asd"], ["qwe"], ["qwe"]], itemgetter(0), [["asd"], ["qwe"]]),
		([0, 1, 1, 2], identity, [0, 1, 2]),
	)
	def test_delete_duplicates_from_sorted_sequence(self, seq, key, truth):
		delete_duplicates_from_sorted_sequence(seq, key) # inplace
		self.assertIterEqual(truth, seq)

if __name__ == "__main__":
	import unittest
	unittest.main()
