from __future__ import absolute_import, division, print_function, unicode_literals

from sys import stdout
from functools import wraps, reduce, partial
from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from typing import Callable, Any, TextIO, Iterable, Iterator

def identity(x):
	# type: (T, ) -> T

	""" Identity function. """

	return x

def nop():
	# type: () -> None

	""" Function which does absolutely nothing (aka pass, noop). """

	pass

def partial_decorator(*args, **kwargs):
	# type: (*Any, **Any) -> Callable

	""" Same as `functools.partial` but applied as a decorator. """

	def decorator(func):
		return partial(func, *args, **kwargs)
	return decorator

def compose_two(f, g):
	# type: (Callable, Callable) -> Callable

	""" compose_two(f, g) -> lambda x: f(g(x)) """

	return lambda x: f(g(x))

def compose(*functions):
	# type: (Iterable[Callable[[Any], Any]], ) -> Callable[[Any], Any]

	""" compose(f, g, h) -> lambda x: f(g(h(x))).
		see: Function composition
	"""

	return reduce(compose_two, functions, identity)

def apply(f, x): # *args, **kwargs
	# type: (Callable[[T], U], T) -> U

	return f(x)

def zipmap(funcs, vals):
	# type: (Iterable[Callable[[T], U]], Iterable[T]) -> Iterator[U]

	""" applies a list of functions to a list of values """

	return map(apply, funcs, vals)

def multiapply(funcs, elm):
	for func in funcs:
		elm = func(elm)
	return elm

def multimap(funcs, it):
	for i in it:
		yield multiapply(funcs, i)

def call_repeated(num):
	# type: (int, ) -> Callable[[Callable], Callable]

	""" Function decorator to call decorated function `num` times with the same arguments.
		Returns the results of the last call.
	"""

	assert num > 0

	def dec(func):
		@wraps(func)
		def inner(*args, **kwargs):
			last = None
			for i in range(num):
				last = func(*args, **kwargs)
			return last
		return inner
	return dec

def print_return_type(func, file=stdout):
	# type: (Callable, TextIO) -> Callable

	""" Wraps function to print the return type after calling. """

	def inner(*args, **kwargs):
		ret = func(*args, **kwargs)
		print(type(ret), file=file)
		return ret
	return inner
