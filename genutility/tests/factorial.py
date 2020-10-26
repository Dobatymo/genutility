from __future__ import generator_stop

from math import factorial

from genutility.factorial import SplitRecursive
from genutility.test import MyTestCase, parametrize
from genutility.time import PrintStatementTime


class FactorialTest(MyTestCase):

	def setUp(self):
		with PrintStatementTime("Setup took {delta}s"):
			x = (0, 1, 9, 10, 100, 99999, 999999)

			self.tests = {i: factorial(i) for i in x}

	@parametrize(
		(SplitRecursive, )
	)
	def test_factorials(self, cls):
		fac = cls()
		for x, truth in self.tests.items():
			with PrintStatementTime("%s(%s) took {delta}s" % (cls.__name__, x)):
				result = fac.factorial(x)
			self.assertEqual(truth, result)

if __name__ == "__main__":
	import unittest
	unittest.main()
