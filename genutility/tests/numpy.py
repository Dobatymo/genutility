from __future__ import absolute_import, division, print_function, unicode_literals

import numpy as np

from genutility.test import MyTestCase, parametrize, repeat
from genutility.numpy import (remove_color, unblock, decompress, batchtopk, sliding_window_2d, rgb_to_hsi,
	shannon_entropy, is_rgb, is_square, batch_vTAv, batch_inner, batch_outer, logtrace, shiftedexp,
	bincount_batch)
from genutility.math import shannon_entropy as shannon_entropy_python
from genutility.benchmarks.numpy import bincount_batch_2

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
		([], False),
		([0, 0, 0], True),
		([[0, 0, 0]], True),
		([[0, 0, 0], [0, 0, 0]], True),
		([[0], [0], [0]], False),
	)
	def test_is_rgb(self, arr, truth):
		arr = np.array(arr)
		result = is_rgb(arr)
		self.assertEqual(truth, result)

	@parametrize(
		([], False),
		([[]], False),  # fixme: what about this one?
		([[0]], True),
		([[0, 0], [0, 0]], True),
		([[0, 0]], False),
		([[0], [0]], False),
	)
	def test_is_square(self, arr, truth):
		arr = np.array(arr)
		result = is_square(arr)
		self.assertEqual(truth, result)

	@parametrize(
		([[0, 0], [0, 0]], [0, 0], 0),
		([[1, 2], [3, 4]], [5, 6], 319),
		([[[0, 0], [0, 0]]], [[0, 0]], [0]),
		([[[1, 2], [3, 4]]], [[5, 6]], [319]),
		([[[0, 0], [0, 0]], [[1, 2], [3, 4]]], [[0, 0], [5, 6]], [0, 319]),
	)
	def test_batch_vTAv(self, A, v, truth):
		A = np.array(A)
		v = np.array(v)
		result = batch_vTAv(A, v)
		np.testing.assert_equal(truth, result)

	@parametrize(
		([[1, 2], [3, 4]], [5], 250),
		([[[0, 0], [0, 0]], [[1, 2], [3, 4]]], [[5, 6]], [0, 319]),
	)
	def test_batch_vTAv_broadcast(self, A, v, truth):
		A = np.array(A)
		v = np.array(v)
		result = batch_vTAv(A, v)
		np.testing.assert_equal(truth, result)

	@parametrize(
		([], []),
	)
	def test_batch_vTAv_valueerror(self, A, v):
		A = np.array(A)
		v = np.array(v)
		with self.assertRaises(ValueError):
			batch_vTAv(A, v)

	@parametrize(
		([], [], []),
		([0, 0], [0, 0], 0),
		([1, 2], [3, 4], 11),
		([[0, 0]], [[0, 0]], [0]),
		([[1, 2]], [[3, 4]], [11]),
		([[0, 0], [1, 2]], [[0, 0], [3, 4]], [0, 11]),
	)
	def test_batch_inner(self, A, B, truth):
		A = np.array(A)
		B = np.array(B)
		result = batch_inner(A, B)
		np.testing.assert_equal(truth, result)

	@parametrize(
		([1, 2], [2]),
		([[0, 0], [1, 2]], [[3, 4]]),
	)
	def test_batch_inner_valueerror(self, A, B):
		A = np.array(A)
		B = np.array(B)
		with self.assertRaises(ValueError):
			batch_inner(A, B)

	@parametrize(
		([], [], np.empty(shape=(0, 0))),
		([0, 0], [0, 0], [[0, 0], [0, 0]]),
		([1, 2], [3, 4], [[3, 4], [6, 8]]),
		([1, 2], [3], [[3], [6]]),
		([[0, 0], [1, 2]], [[0, 0], [3, 4]], [[[0, 0], [0, 0]], [[3, 4], [6, 8]]]),
	)
	def test_batch_outer(self, A, B, truth):
		A = np.array(A)
		B = np.array(B)
		result = batch_outer(A, B)
		np.testing.assert_equal(truth, result)

	@parametrize(
		([[0], [0]], [0]),
	)
	def test_batch_outer_valueerror(self, A, B):
		A = np.array(A)
		B = np.array(B)
		with self.assertRaises(ValueError):
			batch_outer(A, B)

	@parametrize(
		([[1, 1], [1, 1]], 0.),
		([[1, 2], [3, 4]], 1.3862943611198906),
		([[[1, 1], [1, 1]], [[1, 2], [3, 4]]], [0., 1.3862943611198906]),
	)
	def test_logtrace(self, arr, truth):
		arr = np.array(arr)
		result = logtrace(arr)
		np.testing.assert_allclose(truth, result)

	@parametrize(
		([], []),
		([0, 0], [1., 1.]),
		([1, 2], [0.36787944117144233, 1.]),
		([[0, 0], [1, 2]], [[1., 1.], [0.36787944117144233, 1.]]),
	)
	def test_shiftedexp(self, pvals, truth):
		pvals = np.array(pvals)
		result = shiftedexp(pvals)
		np.testing.assert_allclose(truth, result)

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

	@parametrize(
		([[1, 2], [3, 4]], 0, [[0, 1, 1, 0 ,0], [0, 0, 0, 1, 1]]),
		([[1, 2], [3, 4]], 8, [[0, 1, 1, 0, 0, 0, 0, 0], [0, 0, 0, 1, 1, 0, 0, 0]]),
		([[0]], 0, [[1]]),
	)
	def test_bincount_batch(self, arr, minlength, truth):
		arr, truth = np.array(arr), np.array(truth)

		result = bincount_batch(arr, minlength=minlength)
		np.testing.assert_equal(truth, result)

		result = bincount_batch_2(arr, minlength=minlength)
		np.testing.assert_equal(truth, result)

	@repeat(3)
	def test_bincount_batch_random(self):
		arr = np.random.randint(0, 10000, (1000, 1000))

		result_1 = bincount_batch(arr)
		result_2 = bincount_batch_2(arr)
		np.testing.assert_equal(result_1, result_2)

if __name__ == "__main__":
	import unittest
	unittest.main()
