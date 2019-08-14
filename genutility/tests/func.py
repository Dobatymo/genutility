from __future__ import absolute_import, division, print_function, unicode_literals

from genutility.test import MyTestCase, parametrize
from genutility.func import identity, compose, zipmap, call_repeated

class FuncTest(MyTestCase):

	@parametrize(
		(1,),
		("a",),
	)
	def test_identity(self, input):
		result = identity(input)
		self.assertEqual(input, result)

	@parametrize(
		((lambda x : x + "a",), "", "a"),
		((lambda x : x + "b", lambda x : x + "a"), "", "ab"),
		((lambda x : x + "c", lambda x : x + "b", lambda x : x + "a"), "", "abc")
	)
	def test_compose(self, funcs, input, truth):
		result = compose(*funcs)(input)
		self.assertEqual(truth, result)

	@parametrize(
		((), (), ()),
		((lambda x: x+1,), (0,), (1,)),
		((lambda x: x+1, lambda x: x+2, lambda x: x+3), (1, 2, 3), (2, 4, 6))
	)
	def test_zipmap(self, funcs, vals, truth):
		result = zipmap(funcs, vals)
		self.assertIterEqual(truth, result)

	def test_call_repeated(self):
		self.a = 0
		def adder(self):
			self.a += 1
			return self.a

		result = call_repeated(3)(adder)(self)
		self.assertEqual(3, self.a)
		self.assertEqual(3, result)

if __name__ == '__main__':
	import unittest
	unittest.main()
