from __future__ import absolute_import, division, print_function, unicode_literals

from future.utils import PY2, iteritems

from itertools import chain
from locale import strxfrm
from typing import TYPE_CHECKING

from .iter import switched_enumerate

if TYPE_CHECKING:
	from typing import Iterable, Tuple, Any, IO

english_consonants = "bcdfghjklmnpqrstvwxz" # y?
english_vowels = "aeiouy" # y?

german_consonants = "bcdfghjklmnpqrstvwxyz"
german_vowels = "aeiou"

#def cycleleft(s, start=0, end=-1): # bad
#	return s[:start] + s[start+1:end] + s[start] + s[end+1:]

#def cycleright(s, start=0, end=-1): # bad
#	return s[:start] + s[end] + s[start:end] + s[end+1:]

def tryint(obj):
	try:
		return int(obj)
	except (ValueError, TypeError):
		return obj

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

def deunicode(s):
	# type: (str, ) -> str

	pairs = (("\u2014", "--"), ("\u2017", ">="), ("\u2019", "'"), ("\u2026", "..."))
	s = replace_pairs(s, pairs)
	s.encode("ascii") #check for further unicode
	return s

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

# was: cond_join
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

	s = (r+j+l).join(it)
	if s != "":
		return l+s+r
	return ""

def replace_pairs(s, items):
	# type: (str, Iterable[Tuple[str, str]]) -> str

	for key, value in items:
		s = s.replace(key, value)
	return s

def replace_pairs_bytes(s, items):
	# type: (bytes, Dict[bytes, Optional[bytes]]) -> bytes

	frm = b"".join(k for k, v in iteritems(items) if v)
	to = b"".join(v for k, v in iteritems(items) if v)
	delete = b"".join(k for k, v in iteritems(items) if v is None)

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
		table = {ord(k):v for k, v in iteritems(items)}
	else:
		table = s.maketrans(items)

	return s.translate(table)

def replace_list(s, character_list, replace_char):
	# type: (str, Sequence[str], str) -> str

	""" should work with CaseInsensitiveString also and replace replace_list_insensitive"""

	for find_char in character_list:
		s = s.replace(find_char, replace_char)
	return s
