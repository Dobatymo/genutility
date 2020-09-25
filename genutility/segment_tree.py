from typing import Callable, List, Optional


class SegmentTree(object):

	# ported from https://codeforces.com/blog/entry/18051

	def __init__(self, arr, func, initializer):
		# type: (List[int], Callable[[int, int], int], int) -> None

		self.n = len(arr)
		self.func = func
		self.initializer = initializer

		self.t = [None]*self.n + arr # type: List[Optional[int]]

	def build(self):
		# type: () -> None

		i = self.n - 1
		while i > 0:
			self.t[i] = self.func(self.t[i<<1], self.t[i<<1|1])
			i -= 1

	def modify(self, p, value):
		# type: (int, int) -> None

		p += self.n
		self.t[p] = value

		while p > 1:
			val = self.func(self.t[p], self.t[p^1])
			p >>= 1
			self.t[p] = val

	def query(self, l, r):
		# type: (int, int) -> int

		if l >= r or not 0 <= l <= self.n or not 0 <= r <= self.n:
			raise ValueError("Interval [{}, {}) out of range".format(l, r))

		res = self.initializer
		l += self.n
		r += self.n

		while l < r:

			if l & 1:
				res = self.func(res, self.t[l])
				l += 1
			if r & 1:
				r -= 1
				res = self.func(res, self.t[r])

			l >>= 1
			r >>= 1

		return res

import random
from operator import add
from sys import maxsize
from unittest import TestCase


def range_generator(size, tests):
	ls = random.sample(range(size), tests)
	rs = random.sample(range(size), tests)

	for l, r in zip(ls, rs):
		if l == r:
			continue

		yield min(l, r), max(l, r)

class SegmentTreeTest(TestCase):

	def test_range(self):
		size = 100
		tests = 10

		t = list(range(size))
		random.shuffle(t)

		for func, initializer, truthfunc in (
			(min, maxsize, min),
			(max, -maxsize, max),
			(add, 0, sum)
		):
			st = SegmentTree(t, func, initializer)
			st.build()

			for l, r in range_generator(size, tests):

				result = st.query(l, r)
				truth = truthfunc(t[l:r])
				self.assertEqual(truth, result)

if __name__ == "__main__":
	import unittest
	unittest.main()
