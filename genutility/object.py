from __future__ import absolute_import, division, print_function, unicode_literals

from future.utils import viewitems

from copy import copy
from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from typing import Any

def cast(object, class_, instanceof=object, *args, **kwargs):
	""" Changes the class of `object` to `class_` if `object` is an instance of `instanceof`,
		calls the initializer and returns it.
	"""

	object = copy(object)
	if isinstance(object, instanceof):
		object.__class__ = class_
		object.__init__(*args, **kwargs)
	else:
		raise TypeError("Object is not an instance of {}".format(instanceof.__name__))
	return object

class STAR(object):
	pass

def args_to_key(args, kwargs, separator=STAR):
	# type: (tuple, dict, Any) -> tuple

	""" Create cache key from function arguments.
	"""

	key = []
	if args:
		key.extend(args)
	if kwargs:
		key.append(separator)
		key.extend(sorted(kwargs.items()))

	return tuple(key)

def compress(value):
	# type: (Any, ) -> Any

	""" Creates a copy of the object where some data structures are replaced with equivalent ones
		which take up less space, but are not necessarily mutable anymore.

		tuple < list
		set == frozenset
		bytes < bytearray
	"""

	# sets are not processed because they cannot contain lists or bytearrays anyway.

	if isinstance(value, (tuple, list)): # tuple *can* contain mutables
		return tuple(compress(x) for x in value)
	elif isinstance(value, bytearray):
		return bytes(value) # bytearray can only be bytes or List[int] right?
	elif isinstance(value, dict):
		return {k: compress(v) for k, v in viewitems(value)}
	else:
		return value
