from __future__ import absolute_import, division, print_function, unicode_literals

from future.moves.urllib.parse import urlsplit

from genutility.test import MyTestCase, parametrize
from genutility.url import get_url_argument, url_replace_query

class UrlTest(MyTestCase):

	@parametrize(
		("http://example.com/path?a=1&b=2", "a", "/path", "1"),
		("http://example.com/path?a=1&b=2", "b", "/path", "2"),
		("http://example.com/path?a=1&b=2", "a", None, "1"),
		("http://example.com/path?a=1&b=2", "b", None, "2"),
		("http://example.com/path?a=1&b=2", "a", "path", None),
		("http://example.com/path?a=1&b=2", "b", "path", None),
		("http://example.com/path?a=1&b=2", "c", None, None),
		("http://example.com/path?a=1&b=2", "c", "/path", None),
	)
	def test_get_url_argument(self, url, argument, path, truth):
		s = urlsplit(url)
		result = get_url_argument(s, argument, path)
		self.assertEqual(truth, result)

	@parametrize(
		("http://example.com/path?a=1&b=2#frag", {"a": "3"}, True, "http://example.com/path?a=3"),
		("http://example.com/path?a=1&b=2#frag", {"a": "3"}, False, "http://example.com/path?a=3#frag"),
		("http://example.com/path?a=1&b=2#frag", {"c": "3"}, True, "http://example.com/path?c=3"),
		("http://example.com/path?a=1&b=2#frag", {"c": "3"}, False, "http://example.com/path?c=3#frag")
	)
	def test_url_replace_query(self, url, query, drop_fragment, truth):
		s = urlsplit(url)
		result = url_replace_query(s, query, drop_fragment)
		self.assertEqual(truth, result)

if __name__ == "__main__":
	import unittest
	unittest.main()
