from __future__ import absolute_import, division, print_function, unicode_literals

import sys
from unittest import skipIf
from genutility.test import MyTestCase, parametrize
from genutility.debug import args_str

def ustr(s):
	if sys.version_info >= (3, 0):
		return "'" + s + "'"
	else:
		return "u'" + s + "'"

class DebugTest(MyTestCase):

	def test_args_str(self):
		result = args_str((), {})
		truth = ""
		self.assertEqual(result, truth)

		result = args_str(("asd", 1), {"a":("qwe", 2)}, maxlen=20, app="...")
		truth = "{}, 1, a=({}, 2)".format(ustr("asd"), ustr("qwe"))
		self.assertEqual(result, truth)

	@skipIf(sys.version_info < (3, 0), "Test varies for Python 2 and 3")
	@parametrize(
		(("a",), 2, ".", "'."),
		(("as",), 2, ".", "u's"),
		(("012345678",), 10, "...", "'012345678'"),
		(("0123456789",), 10, "...", "'0123456789'"),
		(("01234567890",), 10, "...", "'01234567890'"),
		(("012345678901",), 10, "...", "'012345678..."),
	)
	def test_args_str_with_app(self, args, maxlen, app, truth):
		result = args_str(args, {}, maxlen, app)
		self.assertEqual(result, truth)

	@skipIf(sys.version_info >= (3, 0), "Test varies for Python 2 and 3")
	@parametrize(
		(("a",), 2, ".", "u'."),
		(("as",), 2, ".", "u'."),
		(("012345678",), 10, "...", "u'012345678'"),
		(("0123456789",), 10, "...", "u'0123456789'"),
		(("01234567890",), 10, "...", "u'01234567..."),
		(("012345678901",), 10, "...", "u'01234567..."),
	)
	def test_args_str_with_app(self, args, maxlen, app, truth):
		result = args_str(args, {}, maxlen, app)
		self.assertEqual(result, truth)

	@skipIf(sys.version_info < (3, 0), "Test varies for Python 2 and 3")
	@parametrize(
		(("01234567",), "'01234567'"),
		(("012345678",), "'012345678'"),
	)
	def test_args_str_without_app(self, args, truth):
		result = args_str(args, {}, maxlen=10, app="")
		self.assertEqual(result, truth)

	@skipIf(sys.version_info >= (3, 0), "Test varies for Python 2 and 3")
	@parametrize(
		(("01234567",), "u'01234567"),
		(("012345678",), "u'01234567"),
	)
	def test_args_str_without_app(self, args, truth):
		result = args_str(args, {}, maxlen=10, app="")
		self.assertEqual(result, truth)

if __name__ == "__main__":
	import unittest
	unittest.main()
