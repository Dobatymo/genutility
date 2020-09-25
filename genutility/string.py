from __future__ import absolute_import, division, print_function, unicode_literals

from builtins import map, zip
from future.utils import PY2, viewitems, viewkeys

import re
from collections import OrderedDict
from functools import partial
from itertools import chain
from locale import strxfrm
from typing import TYPE_CHECKING

from .binary import decode_binary, encode_binary
from .iter import switched_enumerate

if TYPE_CHECKING:
	from typing import Any, Callable, Dict, Iterable, Mapping, Optional, Sequence, Tuple, TypeVar, Union
	T = TypeVar("T")

english_consonants = "bcdfghjklmnpqrstvwxz" # y?
english_vowels = "aeiouy" # y?

german_consonants = "bcdfghjklmnpqrstvwxyz"
german_vowels = "aeiou"

#def cycleleft(s, start=0, end=-1): # bad
#	return s[:start] + s[start+1:end] + s[start] + s[end+1:]

#def cycleright(s, start=0, end=-1): # bad
#	return s[:start] + s[end] + s[start:end] + s[end+1:]

def backslash_escaped_ascii(text):
	# type: (bytes, ) -> str

	return text.decode("ascii", "backslashreplace")

def truncate(text, width, placeholder="..."):
	# type: (str, int, str) -> str

	""" Simple character based truncate method.
		To truncate at word boundaries use `textwrap.shorten`.
	"""

	if width < 0:
		raise ValueError("width cannot be negative")

	if len(placeholder) > width:
		raise ValueError("placeholder cannot be longer then width")

	if len(text) <= width:
		return text
	else:
		return text[0:width - len(placeholder)] + placeholder

def toint(obj, default=None):
	# type: (Any, Optional[T]) -> Union[int, Optional[T]]

	""" Converts `obj` to int if possible and returns `default` otherwise.
	"""

	try:
		return int(obj)
	except (ValueError, TypeError):
		return default

def tryint(obj):
	# type: (T, ) -> Union[int, T]

	""" Converts `obj` to int if possible and returns the original object otherwise.
	"""

	try:
		return int(obj)
	except (ValueError, TypeError):
		return obj

def removeprefix(s, prefix):
	# type: (str, str) -> str

	""" If string `s` starts with `pre` cut it off and return the remaining string. """

	if s.startswith(prefix):
		return s[len(prefix):]
	else:
		return s

def removesuffix(s, suffix):
	# type: (str, str) -> str

	""" If string `s` ends with `suffix` cut it off and return the preceding string. """

	if s.endswith(suffix):
		return s[:-len(suffix)]
	else:
		return s

def encode_case(s):
	# type: (str, ) -> bytes

	""" Encode case information of a string to a bit-encoded bytes string.
	"""

	return encode_binary(c.isupper() for c in s)

def decode_case(s, key):
	# type: (str, bytes) -> str

	""" Apply the case information encoded in `key` to string `s`.
	"""

	return "".join(c.upper() if b else c for c, b in zip(s, decode_binary(key)))

def locale_sorted(seq, case_insensitive=True, lower_before_upper=True):
	if case_insensitive:
		if lower_before_upper:
			key = lambda s: (strxfrm(s.lower()), strxfrm(s.swapcase()))
		else:
			key = lambda s: (strxfrm(s.lower()), strxfrm(s))
	else:
		if lower_before_upper:
			key = lambda s: (strxfrm(s.swapcase()), strxfrm(s))
		else:
			key = strxfrm

	return sorted(seq, key=key)

def build_multiple_replace(d, escape=True):
	# type: (Mapping[str, str], bool) -> Callable[[str], str]

	""" Returns a callable, which when applied to a string,
		replaces all the keys in `d` with the corresponding values.
		The replacement happens in iteration order of the mapping.
		If the order of replacement is important, an OrderedDict should
		be used instead of a dict for Python < 3.7.
		The complexity then is linear in  the length of the input string.
	"""

	if escape:
		it = map(re.escape, viewkeys(d))
	else:
		it = viewkeys(d)

	cp = re.compile("(" + "|".join(it) + ")")
	return partial(cp.sub, lambda m: d[m.group(0)])

def multiple_replace(d, s):
	# type: (Mapping[str, str], str) -> str

	""" Uses mapping `d` to replace keys with values in `s`.
		This is a wrapper for `build_multiple_replace`,
		which should be used directly for improved performance
		in case the same `d` is used for multiple `s`.
	"""

	f = build_multiple_replace(d)
	return f(s)

def replace_multiple(s, d): # cython candidate...
	# type: (Iterable[str], Mapping[str, str]) -> str

	""" Use dictionary `d` to replace instances of key with value.
		If input `s` is a string, the keys must be strings of length 1.
		If the input is an iterable of strings,
		the strings will be compared to the keys for equality.
		The complexity is linear in the length of the iterable/string.
		For string inputs and keys of length > 1 see `multiple_replace`.
	"""

	return "".join(d.get(c, c) for c in s)

def backslash_unescape(s):
	# type: (str, ) -> str

	""" Converts strings with backslash-escaped entities like \n or \u1234
		to a string with these entities.
		Example: backslash_unescape("\\n") -> "\n"
	"""

	# for some reason unicode_escape is based on latin-1
	# ascii also works, but the intermittent string would be longer
	# because more things will be backslash-escaped
	return s.encode("latin-1", "backslashreplace").decode("unicode_escape")

_backslashquote_escape = build_multiple_replace(OrderedDict([
	("\\", "\\\\"),
	("\"", "\\\"")
]))
def backslashquote_escape(s):
	# type: (str, ) -> str

	""" Converts \ to \\ and " to \"
	"""

	return _backslashquote_escape(s)

_backslashquote_unescape = build_multiple_replace(OrderedDict([
	("\\\"", "\""),
	("\\\\", "\\")
]))
def backslashquote_unescape(s):
	# type: (str, ) -> str

	""" Unescapes \\ and \" in `s`.
	"""

	return _backslashquote_unescape(s)

_backslashcontrol_escape = build_multiple_replace(OrderedDict([
	("\\", "\\\\"),
	("\t" ,"\\t"),
	("\n", "\\n"),
	("\r", "\\r")
]))
def backslashcontrol_escape(s):
	# type: (str, ) -> str

	return _backslashcontrol_escape(s)

_backslashcontrol_unescape = build_multiple_replace(OrderedDict([
	("\\\\", "\\"),
	("\\t", "\t"),
	("\\n", "\n"),
	("\\r", "\r")
]))
def backslashcontrol_unescape(s):
	# type: (str, ) -> str

	return _backslashcontrol_unescape(s)

def are_parentheses_matched(s, open="([{", close=")]}"):
	# type: (str, str, str) -> bool

	stack = list()
	parentheses = dict(chain(switched_enumerate(open), switched_enumerate(close)))
	assert len(parentheses) == len(open) + len(close)

	for char in s:
		if char in open:
			stack.append(parentheses[char])
		if char in close:
			try:
				if stack.pop() != parentheses[char]: # wrong nesting
					return False
			except IndexError: # stack empty
				return False

	return len(stack) == 0 # unclosed parentheses left

def filter_join(s, it, func=None):
	# type: (str, Iterable[str], Optional[Callable]) -> str

	if func is None:
		return s.join(i for i in it if i)
	else:
		return s.join(i for i in it if func(i))

def surrounding_join(j, it, l="", r=""):
	# type: (str, Iterable[str], str, str) -> str

	""" Example: surrounding_join(", ", ("a", "b", "c"), l="[", r="]") -> "[a], [b], [c]"
	"""

	s = (r + j + l).join(it)
	if s != "":
		return l + s + r
	return ""

def replace_pairs_bytes(s, items):
	# type: (bytes, Dict[bytes, Optional[bytes]]) -> bytes

	frm = b"".join(k for k, v in viewitems(items) if v)
	to = b"".join(v for k, v in viewitems(items) if v)
	delete = b"".join(k for k, v in viewitems(items) if v is None)

	if PY2:
		import string
		table = string.maketrans(frm, to)
	else:
		table = s.maketrans(frm, to)

	return s.translate(table, delete)

def replace_pairs_chars(s, items):
	# type: (str, Dict[str, Optional[str]]) -> str

	if PY2:
		# table = s.maketrans(items) # 'unicode' object has no attribute 'maketrans'
		table = {ord(k):v for k, v in viewitems(items)}
	else:
		table = s.maketrans(items)

	return s.translate(table)

_contains_digit = re.compile(r"\d")
def contains_digit(s):
	# type: (str, ) -> bool

	""" Tests if a digit is contained in string `s`.
	"""

	return _contains_digit.search(s) is not None
