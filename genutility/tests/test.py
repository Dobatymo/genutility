from __future__ import absolute_import, division, print_function, unicode_literals

from builtins import input
import os.path

from genutility.test import MyTestCase, parametrize
from genutility.test import closeable_tempfile

class MyTestCaseTest(MyTestCase):

	# don't do self.tc = MyTestCase()
	# constructor cannot be called in python, use inheritance only.

	@parametrize(
		(True, True),
	)
	def test_assertAnd(self, a, b):
		self.assertAnd(a, b)

	@parametrize(
		(True, False),
		(False, True),
		(False, False),
	)
	def test_assertAnd_failes(self, a, b):
		with self.assertRaises(AssertionError):
			self.assertAnd(a, b)

	@parametrize(
		([], []),
		([1], [1]),
	)
	def test_assertIterEqual(self, a, b):
		self.assertIterEqual(a, b)

	@parametrize(
		([1], [2]),
		([1], [1, 1]),
	)
	def test_assertIterEqual_failes(self, a, b):
		with self.assertRaises(AssertionError):
			self.assertIterEqual(a, b)

	@parametrize(
		((), ()),
		([1., 2.], [1., 2.]),
		([0.9999999999999999], [1.]),
	)
	def test_assertIterAlmostEqual(self, a, b):
		self.assertIterAlmostEqual(a, b)

	@parametrize(
		([0.9999999], [1.]),
		([1.], [2.]),
		([1.], [1., 1.]),
	)
	def test_assertIterAlmostEqual_failes(self, a, b):
		with self.assertRaises(AssertionError):
			self.assertIterAlmostEqual(a, b)

	@parametrize(
		([], []),
		([(1, 1)], [(1, 1)]),
		([(1, 1), (2, 1)], [(2, 1), (1, 1)]),
		([(1, 0)], []),
		([], [(1, 0)]),
	)
	def test_assertPriorityEqual(self, a, b):
		self.assertPriorityEqual(a, b)

	@parametrize(
		([(1, 1)], []),
		([], [(1, 1)]),
		([(1, 1)], [(1, 0)]),
	)
	def test_assertPriorityEqual_failes(self, a, b):
		with self.assertRaises(AssertionError):
			self.assertPriorityEqual(a, b)

class TestTest(MyTestCase):

	def test_closeable_tempfile(self):
		name = None
		with self.assertRaises(ValueError):
			with closeable_tempfile() as (f, name):
				name = name
				raise ValueError
		self.assertFalse(os.path.exists(name))

	def test_closeable_tempfile_eoferror(self):
		name = None
		with self.assertRaises(EOFError):
			with closeable_tempfile() as (f, name):
				name = name
				raise EOFError
		self.assertFalse(os.path.exists(name))

	def test_closeable_tempfile_ctrlc(self):
		name = None
		with self.assertRaises(KeyboardInterrupt):
			with closeable_tempfile() as (f, name):
				name = name
				input("Press ctrl-c to continue") # this is pretty broken, it first raises EOFError and then shortly after KeyboardInterrupt
		self.assertFalse(os.path.exists(name))

	def test_closeable_tempfile_rw_flush(self):
		truth = b"asd"
		with closeable_tempfile() as (f, name):
			f.write(truth)
			f.flush()
			with open(name, "rb") as fr:
				self.assertEqual(truth, fr.read())
		self.assertFalse(os.path.exists(name))

	def test_closeable_tempfile_rw_close(self):
		truth = b"asd"
		with closeable_tempfile() as (f, name):
			f.write(truth)
			f.close()
			with open(name, "rb") as fr:
				self.assertEqual(truth, fr.read())
		self.assertFalse(os.path.exists(name))

if __name__ == '__main__':
	import unittest
	unittest.main()
