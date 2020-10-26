from __future__ import generator_stop

from genutility.debug import args_str
from genutility.test import MyTestCase, parametrize


class DebugTest(MyTestCase):

	def test_args_str(self):
		result = args_str((), {})
		truth = ""
		self.assertEqual(result, truth)

		result = args_str(("asd", 1), {"a":("qwe", 2)}, maxlen=20, app="...")
		truth = "'{}', 1, a=('{}', 2)".format("asd", "qwe")
		self.assertEqual(result, truth)

	@parametrize(
		(("a",), 2, ".", "'a'"),
		(("as",), 2, ".", "'a."),
		(("012345678",), 10, "...", "'012345678'"),
		(("0123456789",), 10, "...", "'0123456789'"),
		(("01234567890",), 10, "...", "'01234567890'"),
		(("012345678901",), 10, "...", "'012345678..."),
	)
	def test_args_str_with_app(self, args, maxlen, app, truth):
		result = args_str(args, {}, maxlen, app)
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
