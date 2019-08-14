from __future__ import absolute_import, division, print_function, unicode_literals

from itertools import islice

from genutility.test import MyTestCase, parametrize
from genutility.math import (PosInfInt, fibonaccigen, primes, additaet, digitsum_small, digitsum,
	digitsum_base, closest, byte2size, byte2size_str, fibonacci, subblock_indices, limit,
	multinomial_coefficient, argfind_lte, argfind_gte, argmin, argmax, argmax_v2)

class TestPosInfInt(MyTestCase):

	def test_cmp(self):
		self.assertTrue(PosInfInt > 2**128)
		self.assertTrue(PosInfInt > 0)
		self.assertTrue(PosInfInt > -2**128)

		self.assertFalse(PosInfInt < 2**128)
		self.assertFalse(PosInfInt < 0)
		self.assertFalse(PosInfInt < -2**128)

	def test_addsub(self):
		self.assertTrue(PosInfInt + 1 is PosInfInt)
		self.assertTrue(PosInfInt - 1 is PosInfInt)

class MathTest(MyTestCase):

	@parametrize(
		([10, 2, 4, 6, 8, 0], 5, (2, 4)),
		([10, 2, 4, 6, 8, 0], 6, (3, 6)),
	)
	def test_argfind_lte(self, it, target, truth):
		result = argfind_lte(it, target)
		self.assertEqual(truth, result)

	@parametrize(
		([10, 2, 4, 6, 8, 0], 5, (3, 6)),
		([10, 2, 4, 6, 8, 0], 6, (3, 6)),
	)
	def test_argfind_gte(self, it, target, truth):
		result = argfind_gte(it, target)
		self.assertEqual(truth, result)

	@parametrize(
		(0.5, 0.5),
		(-0.5, 0),
		(1.5, 1),
	)
	def test_limit(self, x, truth):
		result = limit(x)
		self.assertEqual(truth, result)

	@parametrize(
		(11, [1, 4, 4, 2], 34650),
	)
	def test_multinomial_coefficient(self, n, ks, truth):
		result = multinomial_coefficient(n, ks)
		self.assertEqual(truth, result)

	@parametrize(
		(0, 1, (0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987)),
		(1, 1, (1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987, 1597))
	)
	def test_fibonaccigen(self, first, second, truth):
		result = islice(fibonaccigen(first, second), len(truth))
		self.assertIterEqual(truth, result)

	@parametrize(
		(10, (2, 3, 5, 7)),
		(None, (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71))
	)
	def test_primes(self, stop, truth):
		result = islice(primes(stop), len(truth))
		self.assertIterEqual(truth, result)

	@parametrize(
		(100, 5050) # Gauss test
	)
	def test_additaet(self, input, truth):
		result = additaet(input)
		self.assertEqual(truth, result)

	@parametrize(
		(1234567890, 45),
		(987654321, 45),
		(9375832, 37),
		(100000000000000000000000000000, 1)
	)
	def test_digitsum(self, number, truth):
		result = digitsum_small(number)
		self.assertEqual(truth, result)
		result = digitsum(number)
		self.assertEqual(truth, result)

	@parametrize(
		(1234567890, 10, 45),
		(987654321, 10, 45),
		(9375832, 10, 37),
		(100000000000000000000000000000, 10, 1),
		("FF", 16, 30)
	)
	def test_digitsum_base(self, number, base, truth):
		result = digitsum_base(number, base)
		self.assertEqual(truth, result)

	@parametrize(
		([1], 1, 1),
		([1], 2, 1),
		([1, 2, 3], 2, 2),
		([1, 4], 2, 1),
		([1., 2., 3.], 2.1, 2),
	)
	def test_closest(self, numbers, number, truth):
		result = closest(numbers, number)
		self.assertEqual(truth, result)

	@parametrize(
		(0, 0, "Byte"),
		(0., 0, "Byte"),
		(1000, 1000, "Byte"),
		(1024**1, 1., "KiB"),
		(1024**2, 1., "MiB"),
		(1024**3, 1., "GiB"),
		(1024**4, 1., "TiB"),
		(1024**5, 1., "PiB"),
		(100000, 97.65625, "KiB"),
		(1024**2+10*1024*1, 1.009765625, "MiB"),
	)
	def test_byte2size(self, number, truth1, truth2):
		num, val = byte2size(number)
		self.assertAlmostEqual(truth1, num)
		self.assertAlmostEqual(truth2, val)

	@parametrize(
		(0, 0, "0 Byte"),
		(0.,  0, "0 Byte"),
		(0, 1, "0 Byte"),
		(1000, 0, "1000 Byte"),
		(1024**1, 1, "1.0 KiB"),
		(1024**2+10*1024, 2, "1.01 MiB"),
		(1024**3, 3, "1.000 GiB"),
		(1024**4, 4, "1.0000 TiB"),
		(1024**5, 5, "1.00000 PiB"),
	)
	def test_byte2size_str(self, number, roundval, truth):
		result = byte2size_str(number, roundval)
		self.assertEqual(truth, result)

	def test_fibonacci(self):
		fibs = [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987, 1597, 2584, 4181, 6765, 10946, 17711, 28657, 46368, 75025, 121393, 196418, 317811, 514229, 832040, 1346269, 2178309, 3524578, 5702887, 9227465, 14930352, 24157817, 39088169, 63245986, 102334155]
		for i, truth in zip(range(100), fibs):
			result = fibonacci(i)
			self.assertEqual(truth, result)

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

	@parametrize(
		([4,7,5,7,8,3,4,2,1], 8),
		([4,7,5,7,8,3,8,1,2], 7)
	)
	def test_argmin(self, input, truth):
		self.assertEqual(truth, argmin(input))

	@parametrize(
		([4,7,5,7,8,3,4,2,1], 4),
		([4,7,5,7,8,3,8,1,2], 4)
	)
	def test_argmax(self, input, truth):
		self.assertEqual(truth, argmax(input))
		self.assertEqual(truth, argmax_v2(input))

if __name__ == "__main__":
	import unittest
	unittest.main()
