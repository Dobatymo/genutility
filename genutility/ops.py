from __future__ import absolute_import, division, print_function, unicode_literals

from future.utils import viewitems

from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from typing import Any, Callable, Sequence, TypeVar
	T = TypeVar("T")

def extract_indexes(d):
	# type: (dict, ) -> Callable([Sequence], dict)

	return lambda seq: {name: seq[index] for index, name in viewitems(d)}

def bit_or(x, y):
	# type: (Any, Any) -> Any

	return x|y

def not_in(s):
	# type: (Container[T], ) -> Callable[[T], bool]

	return lambda x: x not in s

def logical_xor(a, b):
	# type: (Any, Any) -> bool
	# this is just the != operator for bools

	return not (a and b) and (a or b)

def logical_implication(a, b):
	# type: (Any, Any) -> bool

	""" if a is True, b must be True """

	return (not a) or b

def converse_implication(a, b):
	# type: (Any, Any) -> bool

	""" if a is False, b must be False """

	return a or (not b)

def converse_nonimplication(a, b):
	# type: (Any, Any) -> bool

	""" if a is False, b must be True """

	return (not a) and b
