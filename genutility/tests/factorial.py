from __future__ import absolute_import, division, print_function, unicode_literals

from future.utils import PY2, viewitems

from math import factorial

from genutility.factorial import SplitRecursive
from genutility.test import MyTestCase, parametrize
from genutility.time import PrintStatementTime


class FactorialTest(MyTestCase):

	def setUp(self):
		with PrintStatementTime("Setup took {delta}s"):
			if PY2: # python 2 builtin factorial is much slower
				x = (0, 1, 9, 10, 100, 99999)
			else:
				x = (0, 1, 9, 10, 100, 99999, 999999)

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
