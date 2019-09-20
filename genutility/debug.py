import logging
from functools import wraps
from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from typing import Callable, Collection

def _to_union(types):
	# type: (Collection[str], ) -> str

	types = list(set(types))

	if not types:
		return ""
	elif len(types) == 1:
		return types[0]
	elif len(types) > 1:
		return "Union[" + ", ".join(types) + "]"

def _type_str(obj):
	# type: (Any, ) -> str

	return type(obj).__name__

def rec_repr(obj):
	# type: (Any, ) -> str

	if isinstance(obj, defaultdict):
		return _type_str(obj) + "[" + rec_repr(obj.default_factory) + "]"
	elif isinstance(obj, list):
		return "List[" + _to_union(map(rec_repr, obj)) + "]"
	elif isinstance(obj, set):
		return "Set[" + _to_union(map(rec_repr, obj)) + "]"
	else:
		return _type_str(obj)

def log_wrap_call(func):
	# type: (Callable, ) -> Callable

	""" Decorator which logs all calls to function with all arguments """

	@wraps(func)
	def inner(*args, **kwargs):
		logging.debug("START '{}' with {}, {}".format(func.__name__, str(args), str(kwargs)))

		try:
			ret = func(*args, **kwargs)
		except BaseException as e:
			logging.debug("'{}' RAISED '{}' with {}, {}".format(func.__name__, str(e), str(args), str(kwargs)))
			raise

		logging.debug("END '{}' with {}, {}".format(func.__name__, str(args), str(kwargs)))
		return ret
	return inner
