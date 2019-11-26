from __future__ import absolute_import, division, print_function, unicode_literals

from genutility.test import MyTestCase, parametrize
from genutility.debug import args_str

class DebugTest(MyTestCase):

	def test_args_str(self):
		result = args_str((), {})
		truth = ""
		self.assertEqual(result, truth)

		result = args_str(("asd", 1), {"a":("qwe", 2)}, maxlen=20, app="...")
		truth = "'asd', 1, a=('qwe', 2)"
		self.assertEqual(result, truth)

	def test_args_str_with_app(self):
		result = args_str(("a",), {}, maxlen=2, app=".")
		truth = "'a'"
		self.assertEqual(result, truth)

		result = args_str(("as",), {}, maxlen=2, app=".")
		truth = "'a."
		self.assertEqual(result, truth)

		result = args_str(("012345678",), {}, maxlen=10, app="...")
		truth = "'012345678'"
		self.assertEqual(result, truth)

		result = args_str(("0123456789",), {}, maxlen=10, app="...")
		truth = "'0123456789'"
		self.assertEqual(result, truth)

		result = args_str(("01234567890",), {}, maxlen=10, app="...")
		truth = "'01234567890'"
		self.assertEqual(result, truth)

		result = args_str(("012345678901",), {}, maxlen=10, app="...")
		truth = "'012345678..."
		self.assertEqual(result, truth)

	@parametrize(
		(("01234567",), "'01234567'"),
		(("012345678",), "'012345678"),
	)
	def test_args_str_without_app(self, args, truth):
		result = args_str(args, {}, maxlen=10, app="")
		self.assertEqual(result, truth)

if __name__ == "__main__":
	import unittest
	unittest.main()
