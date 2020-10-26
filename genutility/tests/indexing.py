from __future__ import generator_stop

from genutility.indexing import subblock_indices, window_combinations_indices
from genutility.test import MyTestCase, parametrize


class IndexingTest(MyTestCase):

	@parametrize(
		(2, 2, [(0, 1)]),
		(3, 2, [(0, 1), (1, 2)]),
		(4, 3, [(0, 1), (0, 2), (1, 2), (1, 3), (2, 3)]),
	)
	def test_window_combinations_indices(self, size, window_size, truth):
		result = window_combinations_indices(size, window_size)
		self.assertEqual(set(truth), set(result))

	@parametrize(
		(16, 4, 2, [
			[0, 1, 4, 5],
			[0, 1, 4, 5],
			[2, 3, 6, 7],
			[2, 3, 6, 7],
			[0, 1, 4, 5],
			[0, 1, 4, 5],
			[2, 3, 6, 7],
			[2, 3, 6, 7],
			[8, 9, 12, 13],
			[8, 9, 12, 13],
			[10, 11, 14, 15],
			[10, 11, 14, 15],
			[8, 9, 12, 13],
			[8, 9, 12, 13],
			[10, 11, 14, 15],
			[10, 11, 14, 15],
		])
	)
	def test_subblock_indices(self, n, i, j, truths):
		for x, truth in zip(range(n), truths):
			result = list(subblock_indices(x, i, j))
			self.assertEqual(truth, result)

if __name__ == "__main__":
	import unittest
	unittest.main()
