from __future__ import generator_stop

from random import shuffle

from genutility.sort import bubble_sort, selection_sort_max, selection_sort_min
from genutility.test import MyTestCase


class SortTest(MyTestCase):

	def _get_random_list(self):
		lst = list(range(20))
		shuffle(lst)
		return lst

	def test_bubble_sort(self):
		result = self._get_random_list()
		truth = sorted(result)
		bubble_sort(result)
		self.assertEqual(truth, result)

	def test_selection_sort_min(self):
		result = self._get_random_list()
		truth = sorted(result)
		selection_sort_min(result)
		self.assertEqual(truth, result)

	def test_selection_sort_max(self):
		result = self._get_random_list()
		truth = sorted(result)
		selection_sort_max(result)
		self.assertEqual(truth, result)

if __name__ == "__main__":
	import unittest
	unittest.main()
