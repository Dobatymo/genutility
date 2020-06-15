from __future__ import absolute_import, division, print_function, unicode_literals

import numpy as np

from genutility.test import MyTestCase, parametrize
from genutility.numpy import remove_color, unblock, decompress, batchtopk, sliding_window_2d, rgb_to_hsi, shannon_entropy
from genutility.math import shannon_entropy as shannon_entropy_python

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
		remove_color(img, ratio) # inplace
		truth = np.array(truth)
		self.assertTrue(np.array_equal(truth, img))

	@parametrize(
		([1/3, 2/3], 0.9182958340544896),
		([0.5, 0.2, 0.1, 0.1, 0.1], 1.9609640474436814)
	)
	def test_shannon_entropy(self, probabilities, truth):
		result = shannon_entropy(probabilities)
		truth = np.array(truth)
		self.assertAlmostEqual(truth, result)

		result_python = shannon_entropy_python(probabilities)
		self.assertAlmostEqual(result_python, result)

	@parametrize(
		([0., 0., 0.], [0., 0., 0.]), #000000
		([1., 1., 1.], [0., 0., 1.]), # #FFFFFF
		([0.628, 0.643, 0.142], [np.radians(61.5), 0.699, 0.471]), #A0A424
		([0.255, 0.104, 0.918], [np.radians(250.), 0.756, 0.426]), #411BEA
	)
	def test_rgb_to_hsi(self, img, truth):
		""" See: https://en.wikipedia.org/wiki/HSL_and_HSV#Examples (H_2, S_HSI, I) """

		img, truth = np.array(img), np.array(truth)
		result = rgb_to_hsi(img)
		self.assertTrue(np.allclose(truth, result, atol=0, rtol=1e-3), msg=str(result))

	@parametrize(
		([[0, 1], [2, 3]], (1, 1), (1, 1), [[[0]], [[1]], [[2]], [[3]]]),
		(np.arange(9).reshape(3, 3), (2, 2), (1, 1), [[[0, 1], [3, 4]], [[1, 2], [4, 5]], [[3, 4], [6, 7]], [[4, 5], [7, 8]]]),
	)
	def test_sliding_window_2d(self, image, ws, ss, truth):
		image, truth = np.array(image), np.array(truth)
		result = np.array(list(sliding_window_2d(image, ws, ss)))
		self.assertTrue(np.array_equal(truth, result))

	@parametrize(
		([[1,2], [4,3]], None, -1, False, [[1,2], [3,4]]),
		([[1,2], [4,3]], None, -1, True, [[2,1], [4,3]]),
		([[1,2,3,4], [8,7,6,5], [9,10,11,12]], 1, -1, False, [[1], [5], [9]]),
		([[1,2,3,4], [8,7,6,5], [9,10,11,12]], 1, -1, True, [[4], [8], [12]]),
		([[1,2,3,4], [8,7,6,5], [9,10,11,12]], 2, -1, False, [[1,2], [5,6], [9,10]]),
		([[1,2,3,4], [8,7,6,5], [9,10,11,12]], 2, -1, True, [[4,3], [8,7], [12,11]]),
		#([[9,2,3,12], [5,6,7,4], [1,10,11,8]], 2, 0, [[5,9], [6,10], [7,11], [8,12]]),
	)
	def test_batchtopk(self, arr, k, axis, reverse, truth):
		arr, truth = np.array(arr), np.array(truth)
		indices, probs = batchtopk(arr, k, axis, reverse)
		np.testing.assert_equal(truth, probs)

	@parametrize(
		([[1,2], [3,4]], 1, 1, [[1,2,3,4]]),
		([[1,2,3,4], [5,6,7,8], [9,10,11,12], [13,14,15,16]], 2, 2, [[1,2,5,6], [3,4,7,8], [9,10,13,14], [11,12,15,16]]),
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
