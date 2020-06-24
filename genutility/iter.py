from __future__ import absolute_import, division, print_function, unicode_literals

from future.moves.itertools import zip_longest
from future.utils import raise_from
from builtins import zip, map, range, reversed

import sys, logging, random
from collections import deque
from itertools import groupby, chain, tee, islice, count, combinations, product, starmap, repeat
from operator import add
from time import time, sleep
from random import randrange
from types import GeneratorType
from typing import TYPE_CHECKING

from .exceptions import IteratorExhausted, EmptyIterable
from .ops import operator_in

if TYPE_CHECKING:
	from typing import (Any, Callable, Iterable, Iterator, TypeVar, Tuple, Sequence,
		Optional, Collection, List, Union, Type, Dict, TextIO)
	from logging import Logger
	from .typing import SizedIterable, Number
	T = TypeVar("T")
	U = TypeVar("U")
	V = TypeVar("V")

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

def iterrandrange(a, b):
	# type: (int, int) -> Iterator[int]

	""" Yields a stream of non-cryptographic random numbers between `a` (inclusive) and `b` (exclusive).
	"""

	while True:
		yield randrange(a, b)  # nosec

def repeatfunc(func, times=None, *args):
	# type: (Callable[[*Any], T], Optional[int], *any) -> Iterator[T]

	""" Repeat calls to func with specified arguments.
		Example:  repeatfunc(random.random)
		See: https://docs.python.org/3/library/itertools.html#itertools-recipes
	"""

	if times is None:
		return starmap(func, repeat(args))
	return starmap(func, repeat(args, times))

def _lstr(it, length=None):
	if length is None:
		try:
			length = len(it) # type: ignore # TypeError caught below
		except TypeError:
			pass

	if length is not None:
		lstr = "/{}".format(length)
	else:
		lstr = ""

	return length, lstr

def progressdata(it, length=None, refresh=1, end="\r", file=sys.stdout):
	# type: (Union[Iterable, Sequence], Optional[int], float, str, Optional[TextIO]) -> Iterable

	length, lstr = _lstr(it, length)
	last = start = time()
	total = 0

	try:
		for elm in it:
			yield elm
			total += len(elm)
			current = time()
			if current - last > refresh:
				last = current
				duration = current-start
				print("Read {}{}, running for {} seconds ({:0.2e}/s).".format(total, lstr, int(duration), total/duration), end="\r", file=file)
	except KeyboardInterrupt:
		print("Unsafely aborted after reading {}{} in {} seconds ({:0.2e}/s).".format(total, lstr, int(last-start), total/(last-start)), end=end, file=file)
		raise
	else:
		duration = last-start
		if duration > 0:
			print("Finished {} in {} seconds ({:0.2e}/s).".format(total, int(duration), total/duration), end=end, file=file)
		else:
			print("Finished {} in {} seconds.".format(total, int(duration)), end=end, file=file)

def progress(it, length=None, refresh=1, end="\r", file=sys.stdout, extra_info_callback=None):
	# type: (Union[Iterable, Collection], Optional[int], float, str, Optional[TextIO], Callable) -> Iterator

	""" Wraps an iterable `it` to periodically print the progress every `refresh` seconds. """

	""" todo: `from operator import length_hint`
		Use `length_hint(it)` for a guess which might be better than nothing.
		Can return 0.
	"""

	length, lstr = _lstr(it, length)
	extra = ""
	last = start = time()
	i = 0

	for i, elm in enumerate(it, 1):
		yield elm
		current = time()
		if current - last > refresh:
			last = current
			duration = current-start
			if extra_info_callback:
				extra = " [{}]".format(extra_info_callback(i, length))
			print("{}{}, running for {} seconds ({:0.2e}/s){}.".format(i, lstr, int(duration), i/duration, extra), end="\r", file=file)

	duration = last-start
	if duration > 0:
		print("Finished {} in {} seconds ({:0.2e}/s).".format(i, int(duration), i/duration), end=end, file=file)
	else:
		print("Finished {} in {} seconds.".format(i, int(duration)), end=end, file=file)

class Progress(object):

	""" Cannot create a decorator to do this to generic generators,
		because attributes cannot be set on generator objects.
	"""

	def __init__(self, obj):
		self.obj = obj

	def __iter__(self):
		return progress(self.obj)

	def __len__(self):
		# type: () -> int

		""" Can raise a TypeError if underlying object does not support `len()`.
		"""

		return len(self.obj)

def count_distinct(it):
	# type: (Iterable[Any], ) -> int

	return len(set(it))

def reversedzip(*its):
	return zip(*map(reversed, its))

def flatten(it):
	# type: (Union[tuple, list], ) -> Iterator

	for elm in it:
		if isinstance(elm, (tuple, list)):
			for i in flatten(elm):
				yield i
		else:
			yield elm

def diffsgn(a, b):
	# type: (Number, Number) -> int

	""" Sign of the finite derivative.
		Equal to `-cmp(a, b)` or `cmp(b, a).
	"""

	return (a < b) - (a > b)

def asc_peaks(iterable):
	# type: (Iterable[T], ) -> Iterator[T]

	""" Yields ascending peaks from `iterable`. """

	it = iter(iterable)
	try:
		cur = next(it)
	except StopIteration:
		return

	for x in it:
		if x < cur:
			yield cur
		cur = x
	yield cur

def extrema(iterable, first={1, -1}, last={1, -1}, derivatives={1, -1}):
	# type: (Iterable[T], Set[int], Set[int], Set[int]) -> Iterator[T]

	it = iter(iterable)
	try:
		old = next(it)
	except StopIteration:
		return
	try:
		old_2 = next(it)
		old_d = diffsgn(old, old_2)
	except StopIteration:
		yield old # fixme: should this be returned?
		return

	if old_d in first:
		yield old

	old = old_2

	for new in it:
		new_d = diffsgn(old, new)
		if new_d != old_d and old_d in derivatives:
			yield old
		old = new
		old_d = new_d

	if old_d in last:
		yield old

def peaks(it):
	# type: (Iterable[T], ) -> Iterator[T]

	""" Yields peaks of `it`. """

	return extrema(it, {-1}, {1}, {1})

def valleys(it):
	# type: (Iterable[T], ) -> Iterator[T]

	""" Yields valleys of `it`. """

	return extrema(it, {1}, {-1}, {-1})

def empty():
	# type: () -> Iterator

	""" An empty iterator. Other methods include:
		iter(())
		yield from ()
	"""

	return
	yield # pylint: disable=unreachable

def lastdefault(it, default=None):
	# type: (Iterable[T], Optional[T]) -> Optional[T]

	""" Returns the last element of iterable `it`. It discards all other values.
		This method is about 1/2 times as fast as `last()` for large iterables.
	"""

	ret = default
	for i in it:
		ret = i
	return ret

def last(it):
	# type: (Iterable[T], ) -> T

	""" Returns the last element of iterable `it`. It discards all other values.
		This method is about 2 times as fast as `lastdefault()` for large iterables.
	"""

	try:
		return deque(it, 1).pop()
	except IndexError:
		raise_from(EmptyIterable("Empty iterable"), None)

def batch(it, n, func=None):
	# type: (Iterable[Any], int, Optional[Callable]) -> Iterator[Any] # return type cannot be more specific because of filter()

	""" Batches iterable `it` into batches of size `n`.
		Optionally post-processes batch with `func`.
	"""

	it = iter(it)
	while True:
		chunk_it = islice(it, n)
		try:
			first_el = next(chunk_it)
		except StopIteration:
			return

		batch_iter = chain((first_el,), chunk_it)

		if func:
			batch_iter = func(batch_iter)

		yield batch_iter

def advance(it, n):
	# type: (Iterable[T], int) -> None

	""" Advances the iterable `it` n steps. """

	"""
	for i in range(n):
		next(it, None)
	"""
	next(islice(it, n, n), None)

def filternone(it):
	# type: (Iterable, ) -> Iterator

	""" Removes all `None` values from `it`. """

	return (i for i in it if i is not None)

def all_equal(it):
	# type: (Iterable, ) -> bool

	""" Returns `True` if all elements of `it` are equal to each other.

		Much faster than:
			return len(set(it)) in (0, 1)
		and also faster than:
			try:
				first = next(it)
			except StopIteration:
				return True
			return all(first == rest for rest in it)
		for both extreme cases: all equal and none equal
	"""

	g = groupby(it)
	return next(g, True) and not next(g, False) # type: ignore

def pairwise(it):
	# type: (Iterable[T], ) -> Iterator[Tuple[T, T]]

	""" Return two elements of iterable `it` at a time,
		but only advances the iterable by 1 each time.
		pairwise((a, b, c)) -> (a, b), (b, c)
	"""

	a, b = tee(it, 2)
	next(b, None)
	return zip(a, b)

def findfirst(func, it, default=(None, None)):
	# type: (Callable[[T], bool], Iterable[T], Tuple[Optional[int], Optional[T]]) -> Tuple[Optional[int], Optional[T]]

	""" Find the first element of iterable `it` where `func(elm)` evaluates to True.
		Return `default` if not such element was found.
	"""

	for i, x in enumerate(it):
		if func(x):
			return i, x

	return default

def is_empty(it):
	# type: (Iterator, ) -> bool

	""" Returns True if the iterator `it` is already fully consumed.
		If not, it will be advanced.
	"""

	try:
		next(it)
		return False
	except StopIteration:
		return True

def consume(it):
	# type: (Iterable, ) -> None

	""" Consumes the iterable `it` completely. """

	deque(it, maxlen=0)

def resizer(it, size, pad=False, pad_elm=None):
	# type: (Iterable[Sequence[T]], int, bool, Optional[T]) -> Iterable

	""" Cuts the input iterable `it` consisting of variable length slices
		into slices of length `size`. If pad is True, the last slice
		will be padded to length `size` with `pad_elm`.

		resizer(("asd", "qw", "e"), 4) -> (['a', 's', 'd', 'q'], ['w', 'e'])
		resizer(("asd", "qw", "e"), 4, True, "x") -> (['a', 's', 'd', 'q'], ['w', 'e', 'x', 'x'])
	"""

	if size <= 0:
		raise ValueError("size must be larger than 0")

	it = iter(it)
	buf = "" # type: Sequence[T]
	pos = 0
	try:
		while True:
			to_read = size
			out = []
			while to_read > 0:
				if len(buf) == pos:
					buf = next(it)
					pos = 0
				tmp = buf[pos:pos+to_read]
				out.extend(tmp)
				to_read -= len(tmp)
				pos += len(tmp)
			yield out
	except StopIteration:
		if out:
			while pos < len(buf):
				logger.error("this can never happen, can it?")
				tmp = buf[pos:pos+to_read]
				out.extend(tmp)
				to_read -= len(tmp)
				pos += to_read
			if pad:
				yield out + [pad_elm]*(size-len(out))
			else:
				yield out

def switch(it):
	# type: (Iterable[Tuple[T, U]], ) -> Iterator[Tuple[U, T]]

	""" Swaps the elements in iterable of pairs `it`.
		((3, 6), (7, 4), (1, 9)) -> (6, 3), (4, 7), (9, 1)
	"""

	return ((j, i) for i, j in it)

def switched_enumerate(it):
	# type: (Iterable[T], ) -> Iterator[Tuple[T, int]]

	""" Same as `enumerate()` except that order of the output pair is switched.
	"""

	return switch(enumerate(it))

def multi_join(it_a, it_b, join_func=add):
	# type: (Iterable[T], Iterable[U], Callable[[T, U], V]) -> Iterator[V]

	""" Calls `join_func` on the cross product of `it_a` and `it_b`.
		multi_join((1, 2), (3, 4), lambda x, y: str(x)+str(y)) -> ('13', '23', '14', '24')
	"""

	return [join_func(a, b) for b in it_b for a in it_a]

def iter_except(iterator, exception_callbacks, return_on_exception=False):
	# type: (Iterator[T], Dict[Type, Callable[[Iterator[T], Exception], bool]], bool) -> Iterator[T]

	""" Calls callbacks when exceptions are raised in `iterator`. Does not work for Generators.
		The type key in the `exception_callbacks` dict must be the same type as the exception which
		should be caught, not a subtype.
	"""

	if not return_on_exception and isinstance(iterator, GeneratorType):
		raise TypeError("iterator cannot be a generator")

	while True:
		try:
			yield next(iterator)
		except StopIteration:
			return
		except Exception as e:
			try:
				if exception_callbacks[type(e)](iterator, e): # use if x. and not if not x, so None doesn't raise, if user forgets to returns correct value
					raise
			except KeyError:
				raise e
			if return_on_exception:
				return

def list_except(it, catch=Exception):
	# type: (Iterable[T], Union[Exception, Sequence[Exception]]) -> Tuple[Exception, List[T]]

	""" Same as `list()` except in the case of an exception, the partial list which was collected
		so far is returned. `catch` specifies which exceptions are caught. It can be an exception
		or a tuple of exceptions.
	"""

	ret = [] # List[T]
	exc = None # type: Optional[Exception]

	try:
		for i in it:
			ret.append(i)
	except catch as e:
		exc = e

	return exc, ret

def iter_except_ignore(iterator, exceptions, logger=logger):
	# type: (Iterator[T], Collection[Exception], Logger) -> Iterator[T]

	""" Ignores `exceptions` raised in `iterator`. Does not work for Generators.
	"""

	if isinstance(iterator, GeneratorType):
		raise TypeError("iterator cannot be a generator")

	while True:
		try:
			yield next(iterator)
		except StopIteration:
			break
		except exceptions as e:
			logger.warning("Error in iterable: %s", str(e))

def decompress(selectors, data, default=None):
	# type: (Iterable[bool], Iterator[T], Optional[T]) -> Iterator[T]

	""" Basically the opposite of `itertools.compress`.
		decompress([True, False, True], iter(["A", "B"])) -> ("A", None, "B")
	"""

	try:
		for s in selectors:
			if s:
				yield next(data)
			else:
				yield default
	except StopIteration: # exception converted because StopIterations raised in generators will cause RuntimeErrors
		raise IteratorExhausted

def first_not_none(it, default=None):
	# type: (Iterable[T], Optional[T]) -> Optional[T]

	""" Returns the first element of `it` which is not None. """

	return next(filternone(it), default)

def range_count(start=0, stop=None, step=1):
	# type: (int, Optional[int], int) -> Iterator[int]

	""" Similar to `range`, except it optionally allows for an infinite range. """

	if stop:
		return range(start, stop, step)
	else:
		return count(start, step)

def product_range_repeat(depth, args):
	# type: (int, Tuple) -> Iterator

	""" Returns coordinate or coordinate slices useful for iteration over space.
		Can replace higher dimensional for-in-range loops.
	"""

	return product(tuple(range(*args)), repeat=depth)

def powerset(sit):
	# type: (SizedIterable[T], ) -> Iterator[Tuple[T, ...]]

	""" Returns the powerset of a sized iterable.
		The powerset of an empty set is a set including the empty set.

		powerset([1,2,3]) --> (), (1,) (2,) (3,) (1,2) (1,3) (2,3) (1,2,3)
	"""

	return chain.from_iterable(combinations(sit, r) for r in range(len(sit)+1))

def any_in_common(a, b):
	# type: (Iterable[T], Iterable[T]) -> bool

	""" Tests if iterables `a` and `b` have any elements in common.
	"""

	return any(i == j for i, j in product(a, b))

# had cmp=b"\0" default before
def all_equal_to(it, cmp):
	# type: (Iterable[T], T) -> bool

	""" Test if every item of iterable `it` is equal to `cmp`.
	"""

	return all(elm == cmp for elm in it)

def iter_equal(*its):
	# type: (*Iterable, ) -> bool

	""" Test if the contents of all iterables `its` is the same.
	"""

	return all(all_equal(it_elements) for it_elements in zip_longest(*its))

def iter_different(it_a, it_b):
	# type: (Iterable, Iterable) -> bool

	""" Test if `it_a` and `it_b` yield different elements. """

	return any(a != b for a, b in zip_longest(it_a, it_b))

def every_n(it, n, pos=0):
	# type: (Iterable[T], int, int) -> T

	""" Yields every `n`-th element from iterable `it` and starts at `pos`. """

	if pos > 0:
		advance(it, pos)

	for i, val in enumerate(it):
		if i % n == 0:
			yield val

def split(it, size):
	# type: (Iterable[T], int) -> Sequence[Iterable[T]]

	""" memory consumption should be proportional to `size` when output iterators
		are used in parallel loops (like `zip`), else might be higher
	"""

	copies = tee(it, size)
	return tuple(every_n(it, size, pos) for it, pos in zip(copies, range(size)))

def remove_all_dupes(it):
	# type: (Iterable[T], ) -> Iterable[T]

	""" Removes all duplicates from `it` while preserving order. """

	# Dave Kirby
	seen = set()
	return (x for x in it if x not in seen and not seen.add(x))

def retrier(waittime, attempts=-1, multiplier=1, jitter=0, max_wait=None, jitter_dist="uniform", waitfunc=sleep):
	# type: (float, int, float, float, Optional[float], str, Callable[[float], Any]) -> Iterator[None]

	""" Iterator which yields after predefined amounts of time.
		Supports `multiplier` to implements linear or exponential backoff.
		`jitter` adds noise to the average wait time, distributed according to `jitter_dist`.
		Supported values for `jitter_dist` are `uniform` and `normal`.
	"""

	if jitter_dist == "uniform":
		rand = random.uniform
	elif jitter_dist == "normal":
		rand = random.normalvariate
	else:
		raise ValueError("Unsupported jitter_dist")

	if attempts == 0:
		return

	for i in count():
		yield i

		attempts -= 1

		if attempts != 0:
			if max_wait and waittime > max_wait:
				jitter *= max_wait/waittime
				waittime = max_wait
				multiplier = 1

			do_wait = max(0, waittime + rand(-jitter, jitter))
			waitfunc(do_wait)
		else:
			break

		waittime *= multiplier
		jitter *= multiplier

def collapse_any(it, col_set):
	# type: (Iterable[T], Set[T]) -> Iterator[T]

	""" Removes consecutive elements from iterable `it` if element is in `col_set`.
		([1,1,2,2,3,3,4,4], {1,2}) -> 1, 2, 3, 3, 4, 4
	"""

	assert isinstance(col_set, set)

	for key, g in groupby(it):
		if key in col_set:
			yield key
		else:
			for i in g: # yield from g
				yield i

def collapse_all(it, col_set, replacement):
	# type: (Iterable[T], Set[T], T) -> Iterator[T]

	""" Removes consecutive elements from iterable `it` if element is in `col_set`
		and replace `replacement`.
		([1,1,2,2,3,3,4,4], {1,2}, 5) -> 5, 3, 3, 4, 4
	"""

	assert isinstance(col_set, set)

	for key, g in groupby(it, key=operator_in(col_set)):
		if key:
			yield replacement
		else:
			for i in g: # yield from g
				yield i
