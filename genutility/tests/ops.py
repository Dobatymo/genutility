from __future__ import generator_stop

from genutility.ops import (bit_or, converse_implication, converse_nonimplication, logical_implication,
                            logical_nonimplication, logical_xnor, logical_xor, operator_in)
from genutility.test import MyTestCase, parametrize


class OpsTest(MyTestCase):

	@parametrize(
		([1,2,3], 1, True),
		({1,2,3}, 4, False)
	)
	def test_operator_in(self, s, elm, truth):
		result = operator_in(s)(elm)
		self.assertEqual(truth, result)

	@parametrize(
		(0, 0, 0),
		(0, 1, 1),
		(1, 0, 1),
		(1, 1, 1),
		(0, 2, 2),
		(2, 0, 2),
		(2, 2, 2)
	)
	def test_bit_or(self, x, y, truth):
		result = bit_or(x, y)
		self.assertEqual(truth, result)

	@parametrize(
		(True, True, True),
		(True, False, True),
		(False, True, False),
		(False, False, True)
	)
	def test_converse_implication(self, a, b, truth):
		result = converse_implication(a, b)
		self.assertEqual(truth, result)

	@parametrize(
		(True, True, False),
		(True, False, False),
		(False, True, True),
		(False, False, False)
	)
	def test_converse_nonimplication(self, a, b, truth):
		result = converse_nonimplication(a, b)
		self.assertEqual(truth, result)

	@parametrize(
		(True, True, False),
		(True, False, True),
		(False, True, True),
		(False, False, False)
	)
	def test_logical_xor(self, a, b, truth):
		result = logical_xor(a, b)
		self.assertEqual(truth, result)

	@parametrize(
		("a", "b", False), # should be None
		("a", None, "a"),
		(None, "b", "b"),
		(None, None, None)
	)
	def test_logical_xor_nonbool(self, a, b, truth):
		result = logical_xor(a, b)
		self.assertEqual(truth, result)

	@parametrize(
		(True, True, True),
		(True, False, False),
		(False, True, True),
		(False, False, True)
	)
	def test_logical_implication(self, a, b, truth):
		result = logical_implication(a, b)
		self.assertEqual(truth, result)

	@parametrize(
		(True, True, True),
		(True, False, False),
		(False, True, False),
		(False, False, True)
	)
	def test_logical_xnor(self, a, b, truth):
		result = logical_xnor(a, b)
		self.assertEqual(truth, result)

	@parametrize(
		("a", "b", "b"),
		("a", None, None),
		(None, "b", None),
		(None, None, True) # should be None
	)
	def test_logical_xnor_nonbool(self, a, b, truth):
		result = logical_xnor(a, b)
		self.assertEqual(truth, result)

	@parametrize(
		(True, True, False),
		(True, False, True),
		(False, True, False),
		(False, False, False)
	)
	def test_logical_nonimplication(self, a, b, truth):
		result = logical_nonimplication(a, b)
		self.assertEqual(truth, result)

if __name__ == "__main__":
	import unittest
	unittest.main()
