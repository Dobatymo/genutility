from __future__ import generator_stop

import logging
import random
import sys
from collections import deque
from functools import partial
from itertools import chain, combinations, count, groupby, islice, product, repeat, starmap, tee, zip_longest
from operator import add, itemgetter
from random import randrange
from time import sleep, time
from types import GeneratorType
from typing import (TYPE_CHECKING, Any, Callable, Collection, Container, Dict, Generic, Iterable, Iterator, List,
                    Optional, Sequence, Set, TextIO, Tuple, Type, TypeVar, Union)

from .exceptions import EmptyIterable, IteratorExhausted
from .ops import operator_in

if TYPE_CHECKING:
	from .typing import Orderable, SizedIterable

	OrderableT = TypeVar("OrderableT", bound=Orderable)
	ExceptionsType = Union[Type[Exception], Tuple[Type[Exception], ...]]

T = TypeVar("T")
U = TypeVar("U")
V = TypeVar("V")

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

def one(it):
	# type: (Iterator[T], ) -> T

	try:
		ret = next(it)
	except StopIteration:
		raise EmptyIterable()
	try:
		next(it)
	except StopIteration:
		pass
	else:
		raise ValueError("Iterator yielded more than one value")

	return ret

def iterrandrange(a, b):
	# type: (int, int) -> Iterator[int]

	""" Yields a stream of non-cryptographic random numbers between `a` (inclusive) and `b` (exclusive).
	"""

	while True:
		yield randrange(a, b)  # nosec

def repeatfunc(func, times=None, *args):
	# type: (Callable[..., T], Optional[int], *Any) -> Iterator[T]

	""" Repeat calls to func with specified arguments.
		Example:  repeatfunc(random.random)
		See: https://docs.python.org/3/library/itertools.html#itertools-recipes
	"""

	if times is None:
		return starmap(func, repeat(args))
	return starmap(func, repeat(args, times))

def _lstr(it, length=None):
	# type: (Iterable, Optional[int]) -> Tuple[Optional[int], str]

	if length is None:
		try:
			length = len(it)
		except TypeError:
			pass

	if length is not None:
		lstr = f"/{length}"
	else:
		lstr = ""

	return length, lstr

def progress(it, length=None, refresh=1, end="\r", file=sys.stdout, extra_info_callback=None, disable=False, delta=1):
	# type: (Union[Iterable, Collection], Optional[int], float, str, Optional[TextIO], Optional[Callable[[int, Optional[int]], str]], bool, Optional[int]) -> Iterator

	""" Wraps an iterable `it` to periodically print the progress every `refresh` seconds.
		`lengths` is the total size of `it`. `len(it)` is used to get the size if set to `None`.
		`refresh` updates the printed output every `refresh` seconds.
		`delta` specifies the value which is added to the counter every iteration.
			`None` uses `len(elm)` to determine the value. Defaults to 1.
	"""

	""" todo: `from operator import length_hint`
		Use `length_hint(it)` for a guess which might be better than nothing.
		Can return 0.
	"""

	if delta is not None and delta < 1:
		raise ValueError(f"`delta` must be a integer larger than 1 or `None`, not '{delta}'")

	if disable:
		return it

	length, lstr = _lstr(it, length)
	extra = ""
	last = start = time()
	total = 0

	try:
		for elm in it:
			yield elm
			if delta is None:
				total += len(elm)
			else:
				total += delta
			current = time()
			if current - last > refresh:
				last = current
				duration = current - start
				if extra_info_callback:
					extra = extra_info_callback(total, length)
					extra = f" [{extra}]"
				print(f"{total}{lstr}, running for {int(duration)} seconds ({total/duration:0.2e}/s){extra}.", end="\r", file=file)
	except KeyboardInterrupt:
		duration = last - start
		if duration > 0:
			print(f"Unsafely aborted after reading {total}{lstr} in {int(duration)} seconds ({total/duration:0.2e}/s).", end=end, file=file)
		else:
			print(f"Unsafely aborted after reading {total}{lstr} in {int(duration)} seconds.", end=end, file=file)
		raise
	else:
		duration = last - start
		if duration > 0:
			print(f"Finished {total} in {int(duration)} seconds ({total/duration:0.2e}/s).", end=end, file=file)
		else:
			print(f"Finished {total} in {int(duration)} seconds.", end=end, file=file)

def progressdata(it, length=None, refresh=1, end="\r", file=sys.stdout, extra_info_callback=None, disable=False):
	# type: (Union[Iterable, Collection], Optional[int], float, str, Optional[TextIO], Optional[Callable[[int, Optional[int]], str]], bool) -> Iterable

	return progress(it, length, refresh, end, file, extra_info_callback, disable, None)

class Progress(object):

	""" Cannot create a decorator to do this to generic generators,
		because attributes cannot be set on generator objects.
	"""

	def __init__(self, obj, refresh=1):
		# type: (Collection, float) -> None

		self.obj = obj
		self.refresh = refresh

	def __iter__(self):
		# type: () -> Iterator

		return progress(self.obj, len(self.obj), self.refresh)

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
	# type: (OrderableT, OrderableT) -> int

	""" Sign of the finite derivative.
		Equal to `-cmp(a, b)` or `cmp(b, a).
	"""

	return (a < b) - (a > b)

def asc_peaks(iterable):
	# type: (Iterable[OrderableT], ) -> Iterator[OrderableT]

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
	# type: (Iterable[OrderableT], Set[int], Set[int], Set[int]) -> Iterator[OrderableT]

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
	# type: (Iterable[OrderableT], ) -> Iterator[OrderableT]

	""" Yields peaks of `it`. """

	return extrema(it, {-1}, {1}, {1})

def valleys(it):
	# type: (Iterable[OrderableT], ) -> Iterator[OrderableT]

	""" Yields valleys of `it`. """

	return extrema(it, {1}, {-1}, {-1})

def empty():
	# type: () -> Iterator

	""" An empty iterator. Other methods include:
		iter(())
		yield from ()
	"""

	return
	yield # type: ignore # pylint: disable=unreachable

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
		raise EmptyIterable("Empty iterable") from None

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

def x_wise(it, size):
	# type: (Iterable, int) -> Iterator

	""" Returns `size` elements of iterable `it`, but only advances the iterable by 1 each time.
		([1,2,3,4,5], 2) -> [1,2], [2,3], [3,4], [4,5]
		([1,2,3,4,5], 3) -> [1,2,3], [2,3,4], [3,4,5]
		([1,2,3,4,5], 4) -> [1,2,3,4], [2,3,4,5]
		and so only
	"""

	copies = tee(it, size)
	for copy, pos in zip(copies, range(size)):
		advance(copy, pos)
	return zip(*copies)

triples = partial(x_wise, size=3)

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
	# type: (Iterable[Sequence[T]], int, bool, Optional[T]) -> Iterable[List[Optional[T]]]

	""" Cuts the input iterable `it` consisting of variable length slices
		into slices of length `size`. If pad is True, the last slice
		will be padded to length `size` with `pad_elm`.

		resizer(("asd", "qw", "e"), 4) -> (['a', 's', 'd', 'q'], ['w', 'e'])
		resizer(("asd", "qw", "e"), 4, True, "x") -> (['a', 's', 'd', 'q'], ['w', 'e', 'x', 'x'])
	"""

	if size <= 0:
		raise ValueError("size must be larger than 0")

	it = iter(it)
	buf = [] # type: Sequence[T]
	pos = 0
	try:
		while True:
			to_read = size
			out = []  # type: List[Optional[T]]
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

	return (join_func(a, b) for b in it_b for a in it_a)

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
	# type: (Iterable[T], ExceptionsType) -> Tuple[Optional[Exception], List[T]]

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
	# type: (Iterator[T], ExceptionsType, logging.Logger) -> Iterator[T]

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
	# type: (Iterable[bool], Iterator[T], Optional[T]) -> Iterator[Optional[T]]

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
	# type: (int, Optional[int], int) -> Iterable[int]

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

# had cmp=b"\0" default before
def all_equal_to(it, cmp):
	# type: (Iterable[T], T) -> bool

	""" Test if every item of iterable `it` is equal to `cmp`.
	"""

	return all(elm == cmp for elm in it)

def iter_equal(*its):
	# type: (*Iterable) -> bool

	""" Test if the contents of all iterables `its` is the same.
	"""

	return all(all_equal(it_elements) for it_elements in zip_longest(*its))

def iter_different(it_a, it_b):
	# type: (Iterable, Iterable) -> bool

	""" Test if `it_a` and `it_b` yield different elements. """

	return any(a != b for a, b in zip_longest(it_a, it_b))

def every_n(it, n, pos=0):
	# type: (Iterable[T], int, int) -> Iterator[T]

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

def no_dupes(*its):
	# type: (*Iterable[T]) -> Iterator[T]

	""" Merge `its` and removes all duplicates while preserving order. """

	seen = set()  # type: Set[T]

	for it in its:
		for x in it:
			if x not in seen:
				yield x
				seen.add(x)

def retrier(waittime, attempts=-1, multiplier=1, jitter=0, max_wait=None, jitter_dist="uniform", waitfunc=sleep):
	# type: (float, int, float, float, Optional[float], str, Callable[[float], Any]) -> Iterator[int]

	""" Iterator which yields after predefined amounts of time.
		Supports `multiplier` to implements linear or exponential backoff.
		`jitter` adds noise to the average wait time, distributed according to `jitter_dist`.
		Supported values for `jitter_dist` are `uniform` and `normal`.
	"""

	if jitter_dist == "uniform":
		def rand(waittime, jitter):
			return waittime + random.uniform(-jitter, jitter)  # nosec

	elif jitter_dist == "normal":
		def rand(waittime, jitter):
			return random.normalvariate(waittime, jitter)

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

			do_wait = max(0, rand(waittime, jitter))
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

def any_in_common(a, b):
	# type: (Iterable[T], Iterable[T]) -> bool

	""" Tests if iterables `a` and `b` have any elements in common.
		See also: `any_in`.
	"""

	return any(i == j for i, j in product(a, b))

def any_in(it, container):
	# type: (Iterable[T], Container[T]) -> bool

	""" Tests if any elements of `it` are in `container`.
		For best performance, `container` should be a set.
		See also: `any_in_common`.
	"""

	if isinstance(it, set) and isinstance(container, set):
		return not it.isdisjoint(container)

	return any(elm in container for elm in it)

class CountIter(object):

	""" Example:
		c = CountIter()
		with open("asd.txt", "rt", encoding="utf-8") as fr:
			for line in c.count(fr):
				func(line)  # do something with line
		print("Processed", c.get(), "lines")
	"""

	def __init__(self):
		self.i = 0

	def count(self, it):
		for elm in it:
			self.i += 1
			yield elm

	def get(self):
		return self.i

def select_by_indices(it, indices):
	# type: (Iterable[T], Iterator[int]) -> Iterator[T]

	try:
		sel_ind = next(indices)
		for i, elem in enumerate(it):
			if i == sel_ind:
				yield elem
				sel_ind = next(indices)
	except StopIteration:
		pass

def skip_by_indices(it, indices):
	# type: (Iterator[T], Iterator[int]) -> Iterator[Tuple[int, T]]

	i = 0
	try:
		sel_ind = next(indices)
		for elem in it:
			if i == sel_ind:
				sel_ind = next(indices)
				continue

			yield i, elem
			i += 1
	except StopIteration:
		pass

	for ii, elem in enumerate(it, i):
		yield ii, elem

def remove_consecutive_dupes(it):
	# type: (Iterable, ) -> Iterator

	""" Removes consecutive duplicates from iterable `it`.
		(a, a, b, b, a, b) -> a, b, a, b
	"""

	return map(itemgetter(0), groupby(it))

class CachedIterable(Generic[T]):
	# https://stackoverflow.com/a/19504173

	def __init__(self, iterable):
		# type: (Iterable[T], ) -> None

		self.iterable = iterable
		self.done = False
		self.vals = []  # type: List[T]

	def __iter__(self):
		# type: () -> Iterator[T]

		if self.done:
			return iter(self.vals)
		return chain(self.vals, self._gen_iter())

	def _gen_iter(self):
		# type: () -> Iterator[T]

		for val in self.iterable:
			self.vals.append(val)
			yield val
		self.done = True
