import re
from string import whitespace
from typing import Callable, Iterable, Iterator, Optional, Sequence, Union

from .iter import collapse_all, collapse_any
from .string import replace_multiple
from .unicode import unicode_categories
from .url import get_url_pattern, valid_uri_characters

uni_cats = unicode_categories()


def extract_urls(text: str) -> Iterator[str]:
    """Yields URLs from `text`."""

    pattern = r"https?\:\/\/[" + re.escape(valid_uri_characters) + r"]+"
    for match in re.finditer(pattern, text):
        url = match.group(0)
        yield url


def replace_typographical_punctuation(s: str) -> str:
    """Replaces typographical punctuation with ASCII punctuation."""

    d = {
        "\N{SINGLE LOW-9 QUOTATION MARK}": "'",
        "\N{DOUBLE LOW-9 QUOTATION MARK}": '"',
        "\N{LEFT SINGLE QUOTATION MARK}": "'",
        "\N{RIGHT SINGLE QUOTATION MARK}": "'",
        "\N{LEFT DOUBLE QUOTATION MARK}": '"',
        "\N{RIGHT DOUBLE QUOTATION MARK}": '"',
        "\N{FIGURE DASH}": "-",
        "\N{EN DASH}": "-",
        "\N{EM DASH}": "--",
        "\N{HORIZONTAL BAR}": "--",
        "\N{DOUBLE LOW LINE}": "_",
        "\N{HORIZONTAL ELLIPSIS}": "...",
    }
    return replace_multiple(s, d)


def newlines_to_spaces(s: str) -> str:
    """Replaces newline characters with spaces."""

    d = {
        "\r": "",
        "\n": " ",
        "\u0085": " ",  # should be \N{Next Line} or "\N{NEL}", but python 2.7 doesn't know that name
    }
    return replace_multiple(s, d)


def collapse_whitespace(s: str) -> str:
    """Collapses repeated whitespace into a single space character."""

    # separator_cats = ("Zl", "Zp", "Zs")
    # cats = tuple(uni_cats[i] for i in separator_cats)
    # separators = set.union(*cats)
    return "".join(collapse_all(s, set(whitespace), " "))


def collapse_space(s: str, space: str = " ") -> str:
    """Collapses repeated spaces into a single space character."""

    # slower: variant of this with join
    # slower: re.compile(r" {2,}").sub(" ", s)
    # slower: "".join(collapse_all(s, {" "}, " "))

    if s == space:
        return s

    ss = s.split(space)

    beg = space if not ss[0] else ""
    end = space if not ss[-1] else ""

    return beg + space.join(i for i in ss if i) + end


def collapse_punctuation_symbols(s: str) -> str:
    """Collapses any successive Unicode punctuation symbol in `s`."""

    punctuation_cats = ("Pc", "Pd", "Pe", "Pf", "Pi", "Po", "Ps")
    symbol_cats = ("Sc", "Sk", "Sm", "So")

    cats = tuple(uni_cats[i] for i in punctuation_cats + symbol_cats)
    unwantedset = set.union(*cats)
    return "".join(collapse_any(s, unwantedset))


class ReplaceURLs:
    def __init__(self, replacement: Union[str, Iterable], schemes: Optional[Sequence[str]] = None) -> None:
        if isinstance(replacement, str):
            self.repl: Union[str, Callable[[str], str]] = replacement
        else:
            self.repl = lambda match: next(replacement)  # type: ignore

        self.pattern = get_url_pattern(schemes)

    def __call__(self, s: str, count: int = 0) -> str:
        return self.pattern.sub(self.repl, s, count)
