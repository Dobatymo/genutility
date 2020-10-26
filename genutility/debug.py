from __future__ import absolute_import, division, print_function, unicode_literals

from future.utils import viewitems

import logging
from collections import defaultdict
from functools import wraps
from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from typing import Any, Callable, Collection, Optional

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

def _arg_str(arg, maxlen=None, app="...", repr_args=True):
	# type: (Any, Optional[int], bool) -> str

	if repr_args:
		arg = repr(arg)

	assert isinstance(arg, str)

	if maxlen:
		if len(arg) <= maxlen + len(app):
			return arg
		else:
			return arg[:maxlen] + app
	else:
		return arg

def _kwarg_str(key, value, maxlen=None, app="...", repr_args=True):
	# type: (str, Any, Optional[int], str, bool) -> str

	return key + "=" + _arg_str(value, maxlen, app, repr_args)

def args_str(args, kwargs, maxlen=20, app="...", repr_args=True):
	# type: (tuple, dict, Optional[int], str, bool) -> str

	""" Creates printable string from function arguments.
		If the string needs to be truncated to fit `maxlen`, `app` will be appended.
		The length of `app` is not included in `maxlen`.
		If the original string is shorter or equal `maxlen + len(app)`,
		it will be returned unmodified.
	"""

	args = ", ".join(_arg_str(arg, maxlen, app, repr_args) for arg in args)
	kwargs = ", ".join(_kwarg_str(k, v, maxlen, app, repr_args) for k, v in viewitems(kwargs))

	if args:
		if kwargs:
			return args + ", " + kwargs
		else:
			return args
	else:
		if kwargs:
			return kwargs
		else:
			return ""

def log_call(s):
	# type: (str, ) -> Callable

	""" Decorator to log function calls using template string `s`.
		Available format fields are: 'name', 'args' and 'kwargs'.
	"""

	def dec(func):
		# type: (Callable, ) -> Callable

		def inner(*args, **kwargs):
			logging.debug(s.format(
				name=func.__name__,
				args=args,
				kwargs=kwargs
			))
			return func(*args, **kwargs)
		return inner
	return dec

def log_wrap_call(func):
	# type: (Callable, ) -> Callable

	""" Decorator which logs all calls to `func` with all arguments. """

	@wraps(func)
	def inner(*args, **kwargs):
		logging.debug("START %s(%s)", func.__name__, args_str(args, kwargs))

		try:
			ret = func(*args, **kwargs)
		except BaseException as e:
			logging.exception("RAISED %s(%s)", func.__name__, args_str(args, kwargs))
			raise

		logging.debug("END %s(%s)", func.__name__, args_str(args, kwargs))
		return ret
	return inner

def log_methodcall(func):
	# type: (Callable, ) -> Callable

	""" Decorator to log method calls with arguments. """

	@wraps(func)
	def inner(self, *args, **kwargs):
		classname = self.__class__.__name__
		# classname = type(self).__name__ ?
		logging.debug("%s.%s(%s)", classname, func.__name__, args_str(args, kwargs))
		return func(self, *args, **kwargs)
	return inner

def log_methodcall_result(func):
	# type: (Callable, ) -> Callable

	""" Decorator to log method calls with arguments and results. """

	@wraps(func)
	def inner(self, *args, **kwargs):
		classname = self.__class__.__name__
		# classname = type(self).__name__ ?
		logging.debug("%s.%s(%s)", classname, func.__name__, args_str(args, kwargs))
		res = func(self, *args, **kwargs)
		logging.debug("%s.%s => %s", classname, func.__name__, res)
		return res
	return inner
