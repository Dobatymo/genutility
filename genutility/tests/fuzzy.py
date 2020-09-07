from __future__ import absolute_import, division, print_function, unicode_literals

from genutility.test import MyTestCase
from genutility.fuzzy import extract

class FuzzyTest(MyTestCase):

	choices = ["", "asd", "asd qwe", "ASDF", "ASDF QWE"]

	def test_extract_1(self):
		truth = [("asd", 0), ("ASDF", 1), ("", 3), ("asd qwe", 3), ("ASDF QWE", 4)]
		result = extract("asd", self.choices, max_distance=-1, limit=-1)
		self.assertEqual(truth, result)

	def test_extract_md0(self):
		truth = [("asd", 0)]
		result = extract("asd", self.choices, max_distance=0, limit=-1)
		self.assertEqual(truth, result)

	def test_extract_md1(self):
		truth = [("asd", 0), ("ASDF", 1)]
		result = extract("asd", self.choices, max_distance=1, limit=-1)
		self.assertEqual(truth, result)

	def test_extract_l0(self):
		truth = []
		result = extract("asd", self.choices, max_distance=-1, limit=0)
		self.assertEqual(truth, result)

	def test_extract_l1(self):
		truth = [("asd", 0)]
		result = extract("asd", self.choices, max_distance=-1, limit=1)
		self.assertEqual(truth, result)

	def test_extract_l2(self):
		truth = [("asd", 0), ("ASDF", 1)]
		result = extract("asd", self.choices, max_distance=-1, limit=2)
		self.assertEqual(truth, result)

if __name__ == "__main__":
	import unittest
	unittest.main()
