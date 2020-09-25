from __future__ import absolute_import, division, print_function, unicode_literals

from builtins import str

import re
from string import whitespace
from typing import TYPE_CHECKING

from .iter import collapse_all, collapse_any
from .string import replace_multiple
from .unicode import unicode_categories
from .url import get_url_pattern, valid_uri_characters

if TYPE_CHECKING:
	from typing import Callable, Iterable, Iterator, Optional, Sequence, Union

uni_cats = unicode_categories()

def extract_urls(text):
	# type: (str, ) -> Iterator[str]

	""" Yields URLs from `text`. """

	pattern = r"https?\:\/\/[" + re.escape(valid_uri_characters) + r"]+"
	for match in re.finditer(pattern, text):
		url = match.group(0)
		yield url

def replace_typographical_punctuation(s):
	# type: (str, ) -> str

	""" Replaces typographical punctuation with ASCII punctuation. """

	d = {
		"\N{Single Low-9 Quotation Mark}": "'",
		"\N{Double Low-9 Quotation Mark}": '"',
		"\N{Left Single Quotation Mark}": "'",
		"\N{Right Single Quotation Mark}": "'",
		"\N{Left Double Quotation Mark}": '"',
		"\N{Right Double Quotation Mark}": '"',
		"\N{Figure Dash}": "-",
		"\N{En Dash}": "-",
		"\N{Em Dash}": "--",
		"\N{Horizontal Bar}": "--",
		"\N{Double Low Line}": "_",
		"\N{Horizontal Ellipsis}": "...",
	}
	return replace_multiple(s, d)

def newlines_to_spaces(s):
	# type: (str, ) -> str

	""" Replaces newline characters with spaces. """

	d = {
		"\r": "",
		"\n": " ",
		"\u0085": " ",  # should be \N{Next Line} or "\N{NEL}", but python 2.7 doesn't know that name
	}
	return replace_multiple(s, d)

def collapse_whitespace(s):
	# type: (str, ) -> str

	""" Collapses repeated whitespace into a single space character. """

	# separator_cats = ("Zl", "Zp", "Zs")
	# cats = tuple(uni_cats[i] for i in separator_cats)
	# separators = set.union(*cats)
	return "".join(collapse_all(s, set(whitespace), " "))

def collapse_space(s, space=" "):
	# type: (str, str) -> str

	""" Collapses repeated spaces into a single space character. """

	# slower: variant of this with join
	# slower: re.compile(r" {2,}").sub(" ", s)
	# slower: "".join(collapse_all(s, {" "}, " "))

	if s == space:
		return s

	ss = s.split(space)

	beg = space if not ss[0]  else ""
	end = space if not ss[-1] else ""

	return beg + space.join(i for i in ss if i) + end

def collapse_punctuation_symbols(s):
	# type: (str, ) -> str

	""" Collapses any successive Unicode punctuation symbol in `s`.
	"""

	punctuation_cats = ("Pc", "Pd", "Pe", "Pf", "Pi", "Po", "Ps")
	symbol_cats = ("Sc", "Sk", "Sm", "So")

	cats = tuple(uni_cats[i] for i in punctuation_cats+symbol_cats)
	unwantedset = set.union(*cats)
	return "".join(collapse_any(s, unwantedset))

class ReplaceURLs(object):

	def __init__(self, replacement, schemes=None):
		# type: (Union[str, Iterable], Optional[Sequence[str]]) -> None

		if isinstance(replacement, str):
			self.repl = replacement # type: Union[str, Callable[[str], str]]
		else:
			self.repl = lambda match: next(replacement) # type: ignore

		self.pattern = get_url_pattern(schemes)

	def __call__(self, s, count=0):
		# type: (str, int) -> str

		return self.pattern.sub(self.repl, s, count) # type: ignore # mypy error, `sub()` supports functions as `repl`
