from __future__ import generator_stop

from operator import itemgetter

from genutility.benchmarks.sequence import pop_many_2
from genutility.func import identity
from genutility.sequence import (
    batch,
    cycle_sort,
    delete_duplicates_from_sorted_sequence,
    pop_many,
    sliding_window,
    triangular,
)
from genutility.test import MyTestCase, parametrize


class SequenceTest(MyTestCase):

	@parametrize(
		([], []),
		([1, 2, 3, 4], [(1, 2), (1, 3), (1, 4), (2, 3), (2, 4), (3, 4)]),
	)
	def test_triangular(self, seq, truth):
		result = triangular(seq)
		self.assertIterEqual(truth, result)

	@parametrize(
		([], lambda x: True, [], []),
		([1, 2, 3], lambda x: True, [], [3, 2, 1]),
		([1, 2, 3], lambda x: False, [1, 2, 3], []),
	)
	def test_pop_many(self, seq, func, truth_a, truth_b):
		result = list(pop_many(seq, func))
		self.assertEqual(truth_a, seq)
		self.assertEqual(truth_b, result)

	@parametrize(
		([], lambda x: True, [], []),
		([1, 2, 3], lambda x: True, [], [1, 2, 3]),
		([1, 2, 3], lambda x: False, [1, 2, 3], []),
	)
	def test_pop_many_2(self, seq, func, truth_a, truth_b):
		result = list(pop_many_2(seq, func))
		self.assertEqual(truth_a, seq)
		self.assertEqual(truth_b, result)

	@parametrize(
		([], 0, 1, [[]]),
		([1, 2, 3], 1, 1, [[1], [2], [3]]),
		([1, 2, 3], 2, 1, [[1, 2], [2, 3]]),
		([1, 2, 3], 3, 1, [[1, 2, 3]]),
		([1, 2, 3, 4, 5], 2, 3, [[1, 2], [4, 5]]),
	)
	def test_sliding_window(self, seq, size, step, truth):
		result = sliding_window(seq, size, step)
		self.assertIterEqual(truth, result)

	@parametrize(
		([], 0, 0, [[]]),
	)
	def test_sliding_window_valueerror(self, seq, size, step, truth):
		with self.assertRaises(ValueError):
			list(sliding_window(seq, size, step))

	@parametrize(
		([], 1, []),
		([1, 2, 3], 1, [[1], [2], [3]]),
		([1, 2, 3], 2, [[1, 2], [3]]),
		([1, 2, 3], 3, [[1, 2, 3]]),
	)
	def test_batch(self, seq, size, truth):
		result = batch(seq, size)
		self.assertIterEqual(truth, result)

	@parametrize(
		([], 0, [[]]),
	)
	def test_batch_valueerror(self, seq, size, truth):
		with self.assertRaises(ValueError):
			list(batch(seq, size))

	@parametrize(
		([1, 2, 3], ()),
		([1, 3, 2], ((1, 2),)),
		([3, 2, 1], ((0, 2),)),
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
