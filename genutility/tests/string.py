from __future__ import absolute_import, division, print_function, unicode_literals

from future.utils import iteritems
from random import shuffle

from genutility.test import MyTestCase, parametrize
from genutility.string import replace_list, replace_pairs, are_parentheses_matched, replace_pairs_chars, \
	replace_pairs_bytes, filter_join, surrounding_join, locale_sorted

class StringTest(MyTestCase):

	def test_locale_sorted(self):
		seq = ["a", "b", "c", "A", "B", "C", "aa", "Aa", "aA", "ab", "aB", "BC"]
		truths = {
			(True, True): ['a', 'A', 'aa', 'aA', 'Aa', 'ab', 'aB', 'b', 'B', 'BC', 'c', 'C'],
			(True, False): ['A', 'a', 'Aa', 'aA', 'aa', 'aB', 'ab', 'B', 'b', 'BC', 'C', 'c'],
			(False, True): ['a', 'aa', 'ab', 'aA', 'aB', 'b', 'c', 'A', 'Aa', 'B', 'BC', 'C'],
			(False, False): ['A', 'Aa', 'B', 'BC', 'C', 'a', 'aA', 'aB', 'aa', 'ab', 'b', 'c'],
		}

		for i in range(10):
			shuffle(seq)
			for (ci, lbu), truth in iteritems(truths):
				a = locale_sorted(seq, ci, lbu)
				b = locale_sorted(reversed(seq), ci, lbu)
				self.assertEqual(a, truth)
				self.assertEqual(b, truth)

	@parametrize(
		("asd", "as", "_", "__d"),
		("asd", "sd", "_", "a__"),
	)
	def test_replace_list(self, string, chr_list, replace_char, truth):
		result = replace_list(string, chr_list, replace_char)
		self.assertEqual(truth, result)

	@parametrize(
		("abc", (("a","x"), ("b","y")), "xyc"),
		("abc", (("b","y"), ("c","z")), "ayz"),
	)
	def test_replace_pairs(self, string, items, truth):
		result = replace_pairs(string, items)
		self.assertEqual(truth, result)

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
	def test_surrounding_join(self, s, items, l, r, truth):
		result = surrounding_join(s, items, l, r)
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

if __name__ == '__main__':
	import unittest
	unittest.main()
