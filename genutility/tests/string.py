from __future__ import generator_stop

from random import shuffle

from hypothesis import given, strategies

from genutility.string import (are_parentheses_matched, backslash_unescape, backslashcontrol_escape,
                               backslashcontrol_unescape, backslashquote_escape, backslashquote_unescape, filter_join,
                               locale_sorted, removesuffix, replace_pairs_bytes, replace_pairs_chars, surrounding_join,
                               toint)
from genutility.test import MyTestCase, parametrize


class StringTest(MyTestCase):

	@parametrize(
		("", ""),
		("\\\\", "\\"),
		("\\n", "\n"),
		("\\u1234", "\u1234"),
		("asd\\nasd", "asd\nasd"),
		("\u1234\\n\u1234", "\u1234\n\u1234"),
		("a \\0 \0 \\000 \000 \\x00 \x00 \\u9999 \u9999", "a \0 \0 \000 \000 \x00 \x00 \u9999 \u9999"),
	)
	def test_backslashunescape(self, s, truth):
		result = backslash_unescape(s)
		self.assertEqual(truth, result)

	@parametrize(
		('',),
		('"',),
		('\\',),
		('\\\\',),
		('""',),
		('asd',),
		('"asd"',),
		('\\asd\\',),
		('"asd\\',),
		('\\"\\"',)
	)
	def test_backslashquote_escaping(self, s):
		self.assertEqual(s, backslashquote_unescape(backslashquote_escape(s)))

	@given(strategies.text())
	def test_backslashquote_escaping_2(self, s):
		self.assertEqual(s, backslashquote_unescape(backslashquote_escape(s)))

	@parametrize(
		("asd",),
		("\n",),
		("\\n",),
		("\u1234",),
		("\r\\\\r\u1234",),
		("\\\\t",),
	)
	def test_backslashcontrol_escaping(self, s):
		self.assertEqual(s, backslashcontrol_unescape(backslashcontrol_escape(s)))

	@given(strategies.text())
	def test_backslashcontrol_escaping_2(self, s):
		self.assertEqual(s, backslashcontrol_unescape(backslashcontrol_escape(s)))

	@parametrize(
		(("asd",), None),
		(("1",), 1),
		((1,), 1),
		((None,), None),
		((None, None), None)
	)
	def test_toint(self, inputs, truth):
		result = toint(*inputs)
		self.assertEqual(truth, result)

	@parametrize(
		("", "", ""),
		("ab", "b", "a"),
		("ab", "a", "ab"),
		("asdqwe", "qwe", "asd"),
		("asdqwe", "asd", "asdqwe"),
		("a", "a", ""),
		("asd", "asd", ""),
		("a", "b", "a"),
		("asd", "qwe", "asd"),
	)
	def test_removesuffix(self, s, suffix, truth):
		result = removesuffix(s, suffix)
		self.assertEqual(truth, result)

	def test_locale_sorted(self):
		seq = ["a", "b", "c", "A", "B", "C", "aa", "Aa", "aA", "ab", "aB", "BC"]
		truths = {
			(True, True): ["a", "A", "aa", "aA", "Aa", "ab", "aB", "b", "B", "BC", "c", "C"],
			(True, False): ["A", "a", "Aa", "aA", "aa", "aB", "ab", "B", "b", "BC", "C", "c"],
			(False, True): ["a", "aa", "ab", "aA", "aB", "b", "c", "A", "Aa", "B", "BC", "C"],
			(False, False): ["A", "Aa", "B", "BC", "C", "a", "aA", "aB", "aa", "ab", "b", "c"],
		}

		for i in range(10):
			shuffle(seq)
			for (ci, lbu), truth in truths.items():
				a = locale_sorted(seq, ci, lbu)
				b = locale_sorted(reversed(seq), ci, lbu)
				self.assertEqual(a, truth)
				self.assertEqual(b, truth)

	@parametrize(
		("", True),
		("asd", True),
		("()", True),
		("[]", True),
		("()()", True),
		("()[]", True),
		("(())", True),
		("[[]]", True),
		("([])", True),
		("(([][])[])[]", True),
		("(", False),
		(")", False),
		("()[", False),
		("([)", False),
		("([)]", False),
		("([](])[)", False),
	)
	def test_are_parentheses_matched(self, s, truth):
		result = are_parentheses_matched(s)
		self.assertEqual(truth, result)

	@parametrize(
		(", ", ("a", None, "c"), None, "a, c"),
		(", ", ("a", "b", "c"), lambda x: x != "b", "a, c"),
	)
	def test_filter_join(self, s, items, func, truth):
		result = filter_join(s, items, func)
		self.assertEqual(truth, result)

	@parametrize(
		(", ", (), "", "", ""),
		("", ("a", "b", "c"), "", "", "abc"),
		(", ", ("a", "b", "c"), "(", ")", "(a), (b), (c)"),
	)
	def test_surrounding_join(self, s, items, left, right, truth):
		result = surrounding_join(s, items, left, right)
		self.assertEqual(truth, result)

	@parametrize(
		("abc", {"c": None}, "ab"),
		("abc", {"c": "d"}, "abd"),
		("abc", {"b": "d", "c": None}, "ad"),
		("abc", {"b": "d", "c": "e"}, "ade"),
		("a\u263A", {"a": None}, "\u263A"),
		("a\u263A", {"\u263A": None}, "a"),
		("a\u263A", {"a": "b"}, "b\u263A"),
		("a\u263A", {"\u263A": "\u263B"}, "a\u263B"),
	)
	def test_replace_pairs_chars(self, s, items, truth):
		result = replace_pairs_chars(s, items)
		self.assertEqual(truth, result)

	@parametrize(
		(b"abc", {b"c": None}, b"ab"),
		(b"abc", {b"c": b"d"}, b"abd"),
		(b"abc", {b"b": b"d", b"c": None}, b"ad"),
		(b"abc", {b"b": b"d", b"c": b"e"}, b"ade"),
	)
	def test_replace_pairs_bytes(self, s, items, truth):
		result = replace_pairs_bytes(s, items)
		self.assertEqual(truth, result)

if __name__ == "__main__":
	import unittest
	unittest.main()
