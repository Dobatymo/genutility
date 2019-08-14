from __future__ import absolute_import, division, print_function, unicode_literals

from genutility.test import MyTestCase, parametrize
from genutility.search import bisect_left_generic, make_binary_search, make_binary_search_sequence

class SearchTest(MyTestCase):

	@parametrize(
		(0, 10, 3, 3),
		(3, 4, 3, 3),
	)
	def test_bisect_left_generic(self, lo, hi, input, truth):
		result = bisect_left_generic(lo, hi, make_binary_search(input))
		self.assertEqual(result, truth)

	@parametrize(
		([], 1, 0),
		([-6, -3, 1, 1, 2, 2, 5, 10], 5, 6)
	)
	def test_bisect_left_generic_intlist(self, input, target, truth):
		result = bisect_left_generic(0, len(input), make_binary_search_sequence(input, target))
		self.assertEqual(result, truth)

if __name__ == "__main__":
	import unittest
	unittest.main()
