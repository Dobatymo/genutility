from __future__ import generator_stop

from genutility.cpython import find_local_in_call_stack
from genutility.test import MyTestCase


class CpythonTests(MyTestCase):

	def test_find_local_in_call_stack(self):

		truth = "asd"

		def func_a():
			var_a = truth
			return func_b()

		def func_b():
			return find_local_in_call_stack("func_a", "var_a")

		result = func_a()
		self.assertEqual(truth, result)

	def test_find_local_in_call_stack_error(self):

		truth = "asd"

		def func_a():
			var_b = truth
			return func_b()

		def func_b():
			return find_local_in_call_stack("func_a", "var_a")

		with self.assertRaises(KeyError):
			func_a()

if __name__ == "__main__":
	import unittest
	unittest.main()
