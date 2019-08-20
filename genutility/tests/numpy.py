from __future__ import absolute_import, division, print_function, unicode_literals

import numpy as np

from genutility.test import MyTestCase, parametrize
from genutility.numpy import remove_color, unblock, decompress

RED = [255, 0, 0]
GREEN = [0, 255, 0]
BLUE = [0, 0, 255]

YELLOW = [255, 255, 0]

BLACK = [0, 0, 0]
GRAY = [128, 128, 128]
WHITE = [255, 255, 255]

class NumpyTest(MyTestCase):

	@parametrize(
		([[RED, GREEN], [BLUE, GRAY]], 1, [[RED, GREEN], [BLUE, GRAY]]),
		([[RED, GREEN], [BLUE, GRAY]], 0, [[WHITE, WHITE], [WHITE, GRAY]]),
	)
	def test_remove_color(self, img, ratio, truth):
		img = np.array(img)
		remove_color(img, ratio)
		truth = np.array(truth)
		self.assertTrue(np.array_equal(truth, img))

	@parametrize(
		([[1,2],[3,4]], 1, 1, [[1,2,3,4]]),
		([[1,2,3,4],[5,6,7,8],[9,10,11,12],[13,14,15,16]], 2, 2, [[1,2,5,6],[3,4,7,8],[9,10,13,14],[11,12,15,16]]),
	)
	def test_unblock(self, arr, a, b, truth):
		arr, truth = np.array(arr), np.array(truth)
		result = unblock(arr, a, b)
		np.testing.assert_equal(truth, result)

	@parametrize(
		([], [], 0, []),
		([True], [1], 0, [1]),
		([False], [], 0, [0]),
		([True, False, True], [1, 3], 0, [1, 0, 3]),
	)
	def test_decompress(self, selectors, data, default, truth):
		selectors, data, truth = np.array(selectors, dtype=bool), np.array(data), np.array(truth)
		result = decompress(selectors, data, default)
		np.testing.assert_equal(truth, result)

if __name__ == "__main__":
	import unittest
	unittest.main()
