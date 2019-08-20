from __future__ import absolute_import, division, print_function, unicode_literals

from future.utils import PY2, PY3
import logging
from itertools import chain

from genutility.test import MyTestCase, parametrize
from genutility.iter import (product_range_repeat, every_n, any_in_common, split, remove_all_dupes,
	powerset, iter_except, iter_except_ignore, decompress, iter_equal, IteratorExhausted, consume,
	pairwise, resizer, filternone, all_equal, advance, batch, empty, asc_peaks, peaks, valleys)

try:
	from unittest import mock
except ImportError:
	import mock # backport

nulllogger = logging.getLogger("null")
nulllogger.addHandler(logging.NullHandler())

class IteratorWithException(object):

	def __init__(self):
		self.ret = [
			lambda: 1,
			lambda: 1/0,
			lambda: 2
		]
		self.pos = 0

	def __iter__(self):
		return self

	def __next__(self):
		try:
			func = self.ret[self.pos]
		except IndexError:
			raise StopIteration
		try:
			return func()
		finally:
			self.pos += 1

def GeneratorWithException():
	yield 1
	raise ValueError("some error")
	yield 2

class IterTest(MyTestCase):

	@parametrize(
		(range(0), ),
		(range(1), ),
		(range(2), ),
	)
	def test_consume(self, it):
		it = iter(it)
		consume(it)
		with self.assertRaises(StopIteration):
			next(it)

	@parametrize(
		([], 3, False, []),
		(["asd"], 3, False, ["asd"]),
		(["asd"], 1, False, "asd"),
		(["asd", "qw", "e"], 1, False, "asdqwe"),
		(["asd", "qw", "e"], 2, False, ["as", "dq", "we"]),
		(["asd", "qw", "e"], 3, False, ["asd", "qwe"]),
		(["asd", "qw", "e"], 4, False, ["asdq", "we"]),
		(["asd", "qw", "e"], 5, False, ["asdqw", "e"]),

		([], 3, True, []),
		(["asd"], 3, True, ["asd"]),
		(["asd"], 1, True, "asd"),
		(["asd", "qw", "e"], 1, True, "asdqwe"),
		(["asd", "qw", "e"], 2, True, ["as", "dq", "we"]),
		(["asd", "qw", "e"], 3, True, ["asd", "qwe"]),
		(["asd", "qw", "e"], 4, True, ["asdq", "we__"]),
		(["asd", "qw", "e"], 5, True, ["asdqw", "e____"]),
	)
	def test_resizer(self, it, size, pad, truth):
		result = resizer(it, size, pad, pad_elm="_")
		self.assertIterIterEqual(truth, result)

	@parametrize(
		(0, (0,), [()]),
		(0, (1,), [()]),
		(1, (0,), []),
		(1, (1,), [(0,)]),
		(1, (2,), [(0,), (1,)]),
		(2, (1,), [(0, 0)]),
		(2, (2,), [(0, 0), (0, 1), (1, 0), (1, 1)]),
		(2, (1, 2), [(1, 1)])
	)
	def test_product_range_repeat(self, depth, args, truth):
		result = product_range_repeat(depth, args)
		self.assertIterEqual(truth, result)

	@parametrize(
		(iter((1,2,3,4)), 2, 0, (1,3)),
		(iter((1,2,3,4)), 2, 1, (2,4)),
	)
	def test_every_n(self, it, n, pos, truth):
		result = every_n(it, n, pos)
		self.assertIterEqual(truth, result)

	@parametrize(
		([],[], False),
		([1,2],[2,3], True),
		([1,2],[3,4], False)
	)
	def test_any_in_common(self, a, b, truth):
		result = any_in_common(a, b)
		self.assertEqual(truth, result)

	@parametrize(
		((1,2,3,4,5,6), 1, ((1,2,3,4,5,6),)),
		((1,2,3,4,5,6), 2, ((1,3,5),(2,4,6))),
		((1,2,3,4,5,6), 3, ((1,4),(2,5),(3, 6)))
	)
	def test_split(self, it, size, truth):
		result = (tuple(i) for i in split(it, size))
		self.assertIterEqual(truth, result)

	@parametrize(
		(tuple(), tuple()),
		((1,1,1), (1,)),
		((1,1,2,2,3,3), (1,2,3)),
		((3,3,2,2,1,1), (3,2,1)),
		((1,2,3,1), (1,2,3)),
		((3,2,1,3), (3,2,1)),
	)
	def test_remove_all_dupes(self, input, truth):
		result = remove_all_dupes(input)
		self.assertIterEqual(truth, result)

	@parametrize(
		((1,2,3), ((),(1,),(2,),(3,),(1,2),(1,3),(2,3),(1,2,3))),
	)
	def test_powerset(self, seq, truth):
		result = powerset(seq)
		self.assertIterEqual(truth, result)

	def test_iter_except(self):
		result = tuple(iter_except(iter(tuple()), {}))
		truth = tuple()
		self.assertEqual(truth, result)

	def test_iter_except_ignore(self):
		result = tuple(iter_except_ignore(iter(tuple()), {}))
		truth = tuple()
		self.assertEqual(truth, result)

	def test_iter_except_gen(self):
		with self.assertRaises(TypeError):
			tuple(iter_except(GeneratorWithException(), {}))

	def test_iter_except_ignore_gen(self):
		with self.assertRaises(TypeError):
			tuple(iter_except(GeneratorWithException(), {}))

	def test_iter_except_it(self):
		m = mock.Mock(return_value=None)
		result = tuple(iter_except(IteratorWithException(), {ZeroDivisionError: m}))
		truth = (1,2)
		self.assertEqual(truth, result)
		self.assertEqual(1, m.call_count)

	def test_iter_except_ignore_it(self):
		with self.assertRaises(ZeroDivisionError):
			tuple(iter_except_ignore(IteratorWithException(), ()))

		result = tuple(iter_except_ignore(IteratorWithException(), (ZeroDivisionError, ), nulllogger))
		truth = (1,2)
		self.assertEqual(truth, result)

	@parametrize(
		([True, False, True], iter(["A", "B"]), ("A", None, "B")),
	)
	def test_decompress(self, selectors, data, truth):
		result = decompress(selectors, data)
		self.assertIterEqual(truth, result)

	@parametrize(
		([True, False], iter([])),
	)
	def test_decompress_error(self, selectors, data):
		with self.assertRaises(IteratorExhausted):
			result = tuple(decompress(selectors, data))

	@parametrize(
		(tuple(), tuple()),
		(range(0), tuple()),
		(range(1), tuple()),
		(range(2), ((0, 1),)),
		(range(3), ((0, 1), (1, 2)))
	)
	def test_pairwise(self, input, truth):
		result = pairwise(input)
		self.assertIterEqual(truth, result)

	@parametrize(
		([1], [1]),
		([None], []),
		([1, None], [1])
	)
	def test_filternone(self, it, truth):
		result = filternone(it)
		self.assertIterEqual(truth, result)

	@parametrize(
		(tuple(), True),
		((1,), True),
		((1, 1), True),
		((1, 1, 1), True),
		((1, 2), False),
		((1, 1, 2), False)
	)
	def test_all_equal(self, input, truth):
		result = all_equal(input)
		self.assertEqual(truth, result)

	@parametrize(
		(range(5), 0, 0),
		(range(5), 1, 1),
		(range(5), 2, 2),
	)
	def test_advance(self, it, n, truth):
		it = iter(it)
		advance(it, n)
		self.assertEqual(truth, next(it))

	@parametrize(
		((), 1, ()),
		((), 2, ()),
		((1,), 1, ((1,),)),
		((1, 2), 1, ((1,), (2,))),
		((1, 2), 2, ((1, 2),)),
		((1, 2, 3), 3, ((1, 2, 3),)),
		((0, 0, 1, 1, 2, 2), 2, ((0, 0), (1, 1), (2, 2))),
		((0, 1, 2, 3, 4, 5, 6), 3, ((0, 1, 2), (3, 4, 5), (6, )))
	)
	def test_batch(self, input, size, truth):
		result = batch(input, size)
		self.assertIterIterEqual(truth, result)

	@parametrize(
		(empty(), 1, iter(())),
		(chain.from_iterable((i, i) for i in range(1000000)), 2, zip(range(1000000), range(1000000)))
	)
	def test_batch_lazy(self, input, size, truth): # tests if implementation is really lazy
		result = batch(input, size)
		self.assertIterIterEqual(truth, result)

	def test_empty(self):

		if PY2:
			from collections import Iterable
			from collections import Iterator
			Generator = Iterator
		elif PY3:
			from collections.abc import Iterable
			from collections.abc import Iterator
			from collections.abc import Generator

		it = empty()
		self.assertTrue(isinstance(it, Iterable))
		self.assertTrue(isinstance(it, Iterator))
		self.assertTrue(isinstance(it, Generator))
		with self.assertRaises(StopIteration):
			next(it)
		self.assertEqual(tuple(empty()), tuple())

	@parametrize(
		(([True, False], [True, False], [True, False]), True),
		(([True, False], [True, False], [True, True]), False),
	)
	def test_iter_equal(self, its, truth):
		result = iter_equal(*its)
		self.assertEqual(truth, result)

	@parametrize(
		([], []),
		([1, 2, 1], [2, 1]),
		([2, 1, 2], [2, 2]),
		([1, 2, 3], [3]),
		([3, 2, 1], [3, 2, 1]),
	)
	def test_asc_peaks(self, it, truth):
		result = asc_peaks(it)
		self.assertIterEqual(truth, result)

	@parametrize(
		([1, 2, 3], [3]),
		([3, 2, 1], [3]),
		([1, 2, 3, 2, 1], [3]),
		([3, 2, 1, 2, 3], [3, 3]),
	)
	def test_peaks(self, it, truth):
		result = peaks(it)
		self.assertIterEqual(truth, result)

	@parametrize(
		([1, 2, 3], [1]),
		([3, 2, 1], [1]),
		([1, 2, 3, 2, 1], [1, 1]),
		([3, 2, 1, 2, 3], [1]),
	)
	def test_valleys(self, it, truth):
		result = valleys(it)
		self.assertIterEqual(truth, result)

if __name__ == "__main__":
	import unittest
	unittest.main()
