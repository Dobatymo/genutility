from __future__ import generator_stop

import logging
from itertools import chain, islice
from os import devnull
from unittest.mock import Mock

from hypothesis import given, strategies

from genutility.iter import (
    EmptyIterable,
    IteratorExhausted,
    advance,
    all_equal,
    all_equal_to,
    any_in,
    any_in_common,
    asc_peaks,
    batch,
    collapse_all,
    collapse_any,
    consume,
    count_distinct,
    decompress,
    empty,
    every_n,
    extrema,
    filternone,
    findfirst,
    first_not_none,
    flatten,
    is_empty,
    iter_different,
    iter_equal,
    iter_except,
    iter_except_ignore,
    iterrandrange,
    last,
    lastdefault,
    list_except,
    multi_join,
    no_dupes,
    pairwise,
    peaks,
    powerset,
    product_range_repeat,
    progress,
    remove_consecutive_dupes,
    repeatfunc,
    resizer,
    retrier,
    reversedzip,
    split,
    switch,
    switched_enumerate,
    triples,
    valleys,
    x_wise,
)
from genutility.test import MyTestCase, parametrize

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

	next = __next__

def GeneratorWithException():
	yield 1
	raise ValueError("some error")
	yield 2

class IterTest(MyTestCase):

	def test_progress(self):
		r = range(1000)
		with open(devnull, "w") as fw:
			self.assertIterEqual(r, progress(r, file=fw))

	def test_iterrandrange(self):
		result = set(islice(iterrandrange(0, 10), 100))
		truth = set(range(0, 10))
		self.assertTrue(result <= truth)

	def test_iterrandrange_2(self):
		with self.assertRaises((TypeError, ValueError)):
			next(iterrandrange("a", "b"))

	@parametrize(
		(int, 0, ("1", ), ()),
		(int, 3, ("1", ), (1, 1, 1)),
		(int, 3, ("a", 16), (10, 10, 10)),
	)
	def test_repeatfunc(self, func, times, args, truth):
		result = repeatfunc(func, times, *args)
		self.assertIterEqual(result, truth)

	def test_repeatfunc_2(self):
		result = islice(repeatfunc(int), 3)
		truth = (0, 0, 0)
		self.assertIterEqual(result, truth)

	def test_repeatfunc_3(self):
		with self.assertRaises(TypeError):
			next(repeatfunc(1))

	@parametrize(
		((), 0),
		((1, ), 1),
		((1, 2), 2),
		((1, 2, 1), 2),
		((1, 2, 1, 2), 2),
		(("a"), 1),
		(("aa"), 1),
		(("aaa"), 1),
		(("ab"), 2),
		(("aab"), 2),
		(("aaab"), 2),
		(("abb"), 2),
		(("abbb"), 2),
	)
	def test_count_distinct(self, it, truth):
		result = count_distinct(it)
		self.assertEqual(result, truth)

	@parametrize(
		(None, ),
		(0, ),
	)
	def test_count_distinct_2(self, it):
		with self.assertRaises(TypeError):
			count_distinct(it)

	@parametrize(
		((), []),
		(([], []), []),
		(([], [], []), []),
		(([1, 2, 3], [4, 5, 6]), [(3, 6), (2, 5), (1, 4)]),
		(([1], [2], [3]), [(1, 2, 3)]),
	)
	def test_reversedzip(self, its, truth):
		result = reversedzip(*its)
		self.assertIterEqual(result, truth)

	@given(strategies.lists(strategies.integers()), strategies.lists(strategies.integers()))
	def test_reversedzip_2(self, it1, it2):
		result = list(reversedzip(*reversedzip(*reversedzip(*reversedzip(it1, it2)))))
		if it1 and it2:
			minlen = min(len(it1), len(it2))
			self.assertIterIterEqual(result, [it1[-minlen:], it2[-minlen:]])

	@parametrize(
		((), ()),
		([], []),
		([1, 2, 3], [1, 2, 3]),
		([[1, 2], 3], [1, 2, 3]),
		([[[1], 2], 3], [1, 2, 3]),
		([1, [2, 3]], [1, 2, 3]),
		([1, [2, [3]]], [1, 2, 3]),
		((((1, ), 2), 3), [1, 2, 3]),
		((1, (2, (3, ))), [1, 2, 3]),
		([[1, 2], [3, 4]], [1, 2, 3, 4]),
	)
	def test_flatten(self, it, truth):
		result = flatten(it)
		self.assertIterEqual(result, truth)

	def test_flatten_2(self):
		with self.assertRaises(TypeError):
			next(flatten(1))

	@parametrize(
		([1], 1),
		([1, 2], 2),
	)
	def test_last(self, it, truth):
		result = last(it)
		self.assertEqual(result, truth)

	def test_last_2(self):
		with self.assertRaises(EmptyIterable):
			last([])

	@parametrize(
		([], None),
		([1], 1),
		([1, 2], 2),
	)
	def test_lastdefault(self, it, truth):
		result = lastdefault(it)
		self.assertEqual(result, truth)

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
		([], []),
		([(1, 2)], [(2, 1)]),
		([(1, 2), (3, 4)], [(2, 1), (4, 3)]),
	)
	def test_switch(self, it, truth):
		result = switch(it)
		self.assertIterEqual(truth, result)

	@parametrize(
		([1], ),
		([(1, )], ),
	)
	def test_switch_2(self, it):
		with self.assertRaises((TypeError, ValueError)):
			next(switch(it))

	@parametrize(
		([], []),
		("abc", [("a", 0), ("b", 1), ("c", 2)]),
	)
	def test_switched_enumerate(self, it, truth):
		result = switched_enumerate(it)
		self.assertIterEqual(truth, result)

	@parametrize(
		((1, 2), (3, 4), lambda x, y: x*y, (3, 6, 4, 8)),
		((1, 2), (3, 4), lambda x, y: str(x)+str(y), ("13", "23", "14", "24")),
	)
	def test_multi_join(self, it1, it2, func, truth):
		result = multi_join(it1, it2, func)
		self.assertIterEqual(truth, result)

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
		([], [], False),
		([1,2], [2,3], True),
		([1,2], [3,4], False)
	)
	def test_any_in_common(self, a, b, truth):
		result = any_in_common(a, b)
		self.assertEqual(truth, result)

	@parametrize(
		([], {}, False),
		([1,2], {2,3}, True),
		([1,2], {3,4}, False)
	)
	def test_any_in(self, a, b, truth):
		result = any_in(a, b)
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
	def test_no_dupes(self, input, truth):
		result = no_dupes(input)
		self.assertIterEqual(truth, result)

	@parametrize(
		((1, 2), (3, 4), (1, 2, 3, 4)),
		((1, 2), (2, 3), (1, 2, 3)),
		((4, 1), (2, 3), (4, 1, 2, 3)),
		((4, 1), (2, 1), (4, 1, 2)),
	)
	def test_no_dupes_2(self, input_a, input_b, truth):
		result = no_dupes(input_a, input_b)
		self.assertIterEqual(truth, result)

	@parametrize(
		((), [()]),
		((1,2,1), ((),(1,),(2,),(1,),(1,2),(1,1),(2,1),(1,2,1))),
		((1,2,3), ((),(1,),(2,),(3,),(1,2),(1,3),(2,3),(1,2,3))),
		(range(1, 4), ((),(1,),(2,),(3,),(1,2),(1,3),(2,3),(1,2,3))),
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
			tuple(iter_except_ignore(GeneratorWithException(), {}))

	def test_iter_except_it(self):
		m = Mock(return_value=None)
		result = tuple(iter_except(IteratorWithException(), {ZeroDivisionError: m}))
		truth = (1, 2)
		self.assertEqual(truth, result)
		self.assertEqual(1, m.call_count)

	@parametrize(
		([], (None, [])),
		([1, 2, 3], (None, [1, 2, 3])),
		(GeneratorWithException(), (ValueError(), [1])),
	)
	def test_list_except(self, it, truth):
		exc, result = list_except(it)
		exc_truth, truth = truth
		self.assertEqual(truth, result)
		self.assertTypeEqual(exc_truth, exc)

	def test_iter_except_ignore_it(self):
		with self.assertRaises(ZeroDivisionError):
			tuple(iter_except_ignore(IteratorWithException(), ()))

		result = tuple(iter_except_ignore(IteratorWithException(), (ZeroDivisionError, ), nulllogger))
		truth = (1,2)
		self.assertEqual(truth, result)

	@parametrize(
		([], iter([]), []),
		([True, False, True], iter(["A", "B"]), ("A", None, "B")),
	)
	def test_decompress(self, selectors, data, truth):
		result = decompress(selectors, data)
		self.assertIterEqual(truth, result)

	@parametrize(
		([False, True], iter([])),
		([True, False], iter([])),
	)
	def test_decompress_error(self, selectors, data):
		with self.assertRaises(IteratorExhausted):
			tuple(decompress(selectors, data))

	@parametrize(
		([], None),
		([1], 1),
		([None, 1], 1),
	)
	def test_first_not_none(self, it, truth):
		result = first_not_none(it)
		self.assertEqual(result, truth)

	@parametrize(
		([], []),
		(range(0), tuple()),
		(range(1), tuple()),
		(range(2), ((0, 1),)),
		(range(3), ((0, 1), (1, 2))),
		(range(4), ((0, 1), (1, 2), (2, 3))),
	)
	def test_pairwise(self, input, truth):
		result = pairwise(input)
		self.assertIterEqual(truth, result)

	def test_pairwise_2(self):
		with self.assertRaises(TypeError):
			next(pairwise(1))

	@parametrize(
		((1,2,3,4,5), 2, ((1,2),(2,3),(3,4),(4,5))),
		((1,2,3,4,5), 3, ((1,2,3),(2,3,4),(3,4,5))),
		((1,2,3,4,5), 4, ((1,2,3,4),(2,3,4,5))),
	)
	def test_x_wise(self, it, n, truth):
		result = x_wise(it, n)
		self.assertIterEqual(truth, result)

	@parametrize(
		(tuple(), tuple()),
		(range(1), tuple()),
		(range(2), tuple()),
		(range(3), ((0, 1, 2),)),
		(range(4), ((0, 1, 2), (1, 2, 3)))
	)
	def test_triples(self, input, truth):
		result = tuple(triples(input))
		self.assertEqual(truth, result)

	@parametrize(
		(lambda x: x, [], (None, None)),
		(lambda x: x == 2, [1, 2, 3], (1, 2)),
		(lambda x: x == 4, [1, 2, 3], (None, None)),
	)
	def test_findfirst(self, func, it, truth):
		result = findfirst(func, it)
		self.assertEqual(result, truth)

	@parametrize(
		(iter([]), True),
		(iter([1]), False),
	)
	def test_is_empty(self, it, truth):
		result = is_empty(it)
		self.assertEqual(result, truth)

	@parametrize(
		([], []),
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
		((1, 1, 2), False),
		((1, 2, 2), False),
	)
	def test_all_equal(self, input, truth):
		result = all_equal(input)
		self.assertEqual(truth, result)

	@parametrize(
		(range(5), 0, 0),
		(range(5), 1, 1),
		(range(0), 0, None),
		(range(0), 1, None),
	)
	def test_advance(self, it, n, truth):
		it = iter(it)
		advance(it, n)
		self.assertEqual(truth, next(it, None))

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

		from collections.abc import Generator, Iterable, Iterator

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
		(([], []), False),
		(([True], [True]), False),
		(([True], [False]), True),
		(([True], [True, False]), True),
		(([True, False], [True, True]), True),
		(([True, False], [False, False]), True),
	)
	def test_iter_different(self, its, truth):
		result = iter_different(*its)
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
		([], []),
		([1], [1]),
		([1, 2, 3], [3]),
		([3, 2, 1], [3]),
		([1, 2, 3, 2, 1], [3]),
		([3, 2, 1, 2, 3], [3, 3]),
	)
	def test_peaks(self, it, truth):
		result = peaks(it)
		self.assertIterEqual(truth, result)

	@parametrize(
		([], []),
		([1], [1]),
		([1, 2, 3], [1]),
		([3, 2, 1], [1]),
		([1, 2, 3, 2, 1], [1, 1]),
		([3, 2, 1, 2, 3], [1]),
	)
	def test_valleys(self, it, truth):
		result = valleys(it)
		self.assertIterEqual(truth, result)

	@parametrize(
		({"waittime": 1, "attempts": 3}, [1., 1.]),
		({"waittime": 1, "attempts": 3, "multiplier": 2}, [1., 2.]),
		({"waittime": 1, "attempts": 3, "max_wait": 3}, [1., 1.]),
		({"waittime": 1, "attempts": 5, "multiplier": 2, "max_wait": 3}, [1., 2., 3., 3.]),
	)
	def test_retrier(self, kwargs, truth):
		results = []

		result = tuple(retrier(waitfunc=results.append, **kwargs))
		self.assertIterEqual(truth, results)

		truth = tuple(range(len(truth) + 1))
		self.assertEqual(truth, result)

	@parametrize(
		((), set(), ()),
		((1,1,2,2,3,3,4,4), {1,2}, (1, 2, 3, 3, 4, 4)),
	)
	def test_collapse_any(self, it, set, truth):
		result = collapse_any(it, set)
		self.assertIterEqual(truth, result)

	@parametrize(
		((), set(), None, ()),
		((1,1,2,2,3,3,4,4), {1,2}, 5, (5, 3, 3, 4, 4)),
	)
	def test_collapse_all(self, it, set, replacement, truth):
		result = collapse_all(it, set, replacement)
		self.assertIterEqual(truth, result)

	@parametrize(
		((), ()),
		((1, 2, 3), ()),
		((1, 2, 3, 2, 1), (3, )),
		((1, 2, 1, 2), (2, 1)),
		((2, 1, 2, 1), (1, 2)),
	)
	def test_extrema(self, it, truth):
		result = extrema(it, {}, {})
		self.assertIterEqual(truth, result)

	@parametrize(
		((), 0, True),
		((1, ), 1, True),
		((1, 1), 1, True),
		((1, ), 2, False),
		((1, 2), 1, False),
		((1, 2), 2, False),
	)
	def test_all_equal_to(self, it, elm, truth):
		result = all_equal_to(it, elm)
		self.assertEqual(truth, result)

	@parametrize(
		(tuple(), tuple()),
		((1,1,1), (1,)),
		((1,1,2,2,3,3), (1,2,3)),
		((3,3,2,2,1,1), (3,2,1)),
		((1,2,3,1), (1,2,3,1)),
		((3,2,1,3), (3,2,1,3)),
	)
	def test_remove_consecutive_dupes(self, input, truth):
		result = remove_consecutive_dupes(input)
		self.assertIterEqual(truth, result)

if __name__ == "__main__":
	import unittest
	unittest.main()
