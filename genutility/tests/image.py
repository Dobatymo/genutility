from __future__ import absolute_import, division, print_function, unicode_literals

import numpy as np

from genutility.test import MyTestCase, parametrize
from genutility.image import grayscale, histogram_1d, histogram_2d

class ImageTest(MyTestCase):

	@parametrize(
		([[[1],[2]],[[3],[4]]], [[1,2],[3,4]]),
		([[[1,3],[2,4]],[[3,5],[4,6]]], [[2,3],[4,5]]),
	)
	def test_grayscale(self, img, truth):
		img = np.array(img)
		result = grayscale(img)
		truth = np.array(truth)
		self.assertTrue(np.array_equal(truth, result))

	@parametrize(
		([1,2,3,4], 8, [0, 1, 1, 1, 1, 0, 0, 0]), # single
		([[1,2], [3,4]], 8, [[0, 1, 1, 0, 0, 0, 0, 0], [0, 0, 0, 1, 1, 0, 0, 0]]), # batch
	)
	def test_histogram_1d(self, img, levels, truth):
		img = np.array(img)
		result = histogram_1d(img, levels)
		truth = np.array(truth)
		self.assertTrue(np.array_equal(truth, result))

	@parametrize(
		([[1,2],[3,4]], 8, [0, 1, 1, 1, 1, 0, 0, 0]),
	)
	def test_histogram_2d(self, img, levels, truth):
		img = np.array(img)
		result = histogram_2d(img, levels)
		truth = np.array(truth)
		self.assertTrue(np.array_equal(truth, result))

if __name__ == "__main__":
	import unittest
	unittest.main()
