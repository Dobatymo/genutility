from itertools import count
from typing import Iterator

from genutility.test import MyTestCase, parametrize
from genutility.text import (
    ReplaceURLs,
    collapse_punctuation_symbols,
    collapse_space,
    collapse_whitespace,
    extract_urls,
    newlines_to_spaces,
    replace_typographical_punctuation,
)


def urls_iter() -> Iterator[str]:
    for i in count(0):
        yield f"<URL_{i}>"


class TextTest(MyTestCase):
    @parametrize((" ", " "), ("a  a", "a a"), ("a   a", "a a"), ("a \ta", "a \ta"), ("a \t \ta", "a \t \ta"))
    def test_collapse_space(self, value, truth):
        result = collapse_space(value)
        self.assertEqual(truth, result)

    @parametrize(("a  a", "a a"), ("a   a", "a a"), ("a \ta", "a a"), ("a \t \ta", "a a"))
    def test_collapse_whitespace(self, value, truth):
        result = collapse_whitespace(value)
        self.assertEqual(truth, result)

    @parametrize(("asdaassdd.,..,,", "asdaassdd.,.,"))
    def test_collapse_punctuation_symbols(self, value, truth):
        result = collapse_punctuation_symbols(value)
        self.assertEqual(truth, result)

    @parametrize(
        (urls_iter(), "irc://0.0.0.0", "<URL_0>"),
        (urls_iter(), "asd asd", "asd asd"),
        (urls_iter(), "asd http://localhost asd", "asd <URL_0> asd"),
        (urls_iter(), "asd http://localhost qwe ftp://google.com/ncr zxc", "asd <URL_0> qwe <URL_1> zxc"),
        ("<URL>", "asd https://zh.wikipedia.org/wiki/%E4%B8%AD%E8%8F%AF%E6%B0%91%E5%9C%8B qwe", "asd <URL> qwe"),
        ("<URL>", "asd www.google.com qwe", "asd <URL> qwe"),
    )
    def test_replace_urls(self, replace, input, truth):
        result = ReplaceURLs(replace)(input)
        self.assertEqual(truth, result)

    @parametrize(
        ("", ""),
        ("asd\r\n\rqwe", "asd qwe"),
    )
    def test_newlines_to_spaces(self, s, truth):
        result = newlines_to_spaces(s)
        self.assertEqual(truth, result)

    @parametrize(
        ("", ""),
        ("\N{HORIZONTAL ELLIPSIS}", "..."),
        ("asd\N{HORIZONTAL BAR}qwe", "asd--qwe"),
        ("asd\N{DOUBLE LOW LINE}qwe", "asd_qwe"),
    )
    def test_replace_typographical_punctuation(self, s, truth):
        result = replace_typographical_punctuation(s)
        self.assertEqual(truth, result)

    @parametrize(
        ("", []),
        ("http://asd.com", ["http://asd.com"]),
        ("asd http://asd.com qwe", ["http://asd.com"]),
        ("asd http://asd.com https://asd.com/asd qwe", ["http://asd.com", "https://asd.com/asd"]),
    )
    def test_extract_urls(self, s, truth):
        result = extract_urls(s)
        self.assertIterEqual(truth, result)


if __name__ == "__main__":
    import unittest

    unittest.main()

    """
    import timeit
    print(min(timeit.repeat(stmt="cs(ts)", setup="from __main__ import test_str_short as ts, collapse_space as cs", repeat=5, number=10000)))
    print(min(timeit.repeat(stmt="cs(ts)", setup="from __main__ import test_str_short as ts, collapse_space_2 as cs", repeat=5, number=10000)))
    print(min(timeit.repeat(stmt="cs(ts)", setup="from __main__ import test_str_short as ts, collapse_space_3 as cs", repeat=5, number=10000)))
    print(min(timeit.repeat(stmt="cs(ts)", setup="from __main__ import test_str_short as ts, collapse_space_4 as cs", repeat=5, number=10000)))
    print("---")
    print(min(timeit.repeat(stmt="cs(ts)", setup="from __main__ import test_str_short_ws as ts, collapse_space as cs", repeat=5, number=10000)))
    print(min(timeit.repeat(stmt="cs(ts)", setup="from __main__ import test_str_short_ws as ts, collapse_space_2 as cs", repeat=5, number=10000)))
    print(min(timeit.repeat(stmt="cs(ts)", setup="from __main__ import test_str_short_ws as ts, collapse_space_3 as cs", repeat=5, number=10000)))
    print(min(timeit.repeat(stmt="cs(ts)", setup="from __main__ import test_str_short_ws as ts, collapse_space_4 as cs", repeat=5, number=10000)))
    print("---")
    print(min(timeit.repeat(stmt="cs(ts)", setup="from __main__ import test_str_long as ts, collapse_space as cs", repeat=3, number=1000)))
    print(min(timeit.repeat(stmt="cs(ts)", setup="from __main__ import test_str_long as ts, collapse_space_2 as cs", repeat=3, number=1000)))
    print(min(timeit.repeat(stmt="cs(ts)", setup="from __main__ import test_str_long as ts, collapse_space_3 as cs", repeat=3, number=1000)))
    print(min(timeit.repeat(stmt="cs(ts)", setup="from __main__ import test_str_long as ts, collapse_space_4 as cs", repeat=3, number=1000)))
    print("---")
    print(min(timeit.repeat(stmt="cs(ts)", setup="from __main__ import test_str_long_ws as ts, collapse_space as cs", repeat=3, number=1000)))
    print(min(timeit.repeat(stmt="cs(ts)", setup="from __main__ import test_str_long_ws as ts, collapse_space_2 as cs", repeat=3, number=1000)))
    print(min(timeit.repeat(stmt="cs(ts)", setup="from __main__ import test_str_long_ws as ts, collapse_space_3 as cs", repeat=3, number=1000)))
    print(min(timeit.repeat(stmt="cs(ts)", setup="from __main__ import test_str_long_ws as ts, collapse_space_4 as cs", repeat=3, number=1000)))
    """
