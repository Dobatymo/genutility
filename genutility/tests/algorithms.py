from __future__ import absolute_import, division, print_function, unicode_literals

from genutility.test import MyTestCase, parametrize
from genutility.algorithms import median_of_medians

class AlgorithmsTest(MyTestCase):

	@parametrize(
		([0, 0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 3, 3, 4], 7, 1),
		([1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1], 7, 1),
		([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14], 7, 7),
		([4, 3, 3, 2, 2, 2, 1, 1, 1, 1, 0, 0, 0, 0, 0], 7, 1),
		([1, 1, 1, 1, 1, 1, 1, 3, 3, 3, 3, 3, 3, 3, 2], 7, 3),
		([14, 94, 41, 69, 47, 96, 90, 46, 33, 21, 89, 60, 63, 0, 49], 7, 47),
		([646, 624, 329, 47, 845, 221, 15, 92, 940, 831, 169, 190, 83, 599, 636, 496, 785, 701, 105, 807, 384, 605, 285, 219, 931, 185, 863, 68, 837, 165, 717, 608, 347, 713, 593, 191, 180, 405, 649, 744, 170, 490, 407, 659, 541, 342, 72, 6, 510, 101, 757, 203, 724, 792, 477, 361, 993, 836, 640, 74, 882, 31, 622, 18, 764, 698, 444, 62, 965, 692, 32, 956, 980, 621, 103, 45, 828, 70, 768, 161, 296, 200, 676, 44, 90, 753, 535, 274, 230, 871, 404, 741, 922, 78, 28, 908, 313, 184, 543, 536], 39, 744),
	)
	def test_median_of_medians(self, list, truth_idx, truth_val):
		result = median_of_medians(list)
		self.assertEqual(result, truth_idx)
		self.assertEqual(list[result], truth_val)

if __name__ == "__main__":
	import unittest
	unittest.main()
