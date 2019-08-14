from __future__ import absolute_import, division, print_function, unicode_literals

from future.utils import viewitems
from math import factorial

from genutility.test import MyTestCase, parametrize
from genutility.time import PrintStatementTime
from genutility.factorial import SplitRecursive

class FactorialTest(MyTestCase):

	def setUp(self):
		with PrintStatementTime("Setup took {delta}s"):
			x = (0, 1, 9, 10, 100, 99999, 999999, 9999999)
			self.tests = {i: factorial(i) for i in x}

	@parametrize(
		(SplitRecursive, )
	)
	def test_factorials(self, cls):
		fac = cls()
		for x, truth in viewitems(self.tests):
			with PrintStatementTime("%s(%s) took {delta}s" % (cls.__name__, x)):
				result = fac.factorial(x)
			self.assertEqual(truth, result)

if __name__ == "__main__":
	import unittest
	unittest.main()
