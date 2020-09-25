from __future__ import absolute_import, division, print_function, unicode_literals

from future.utils import viewitems

from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from typing import Any, Callable, Dict, Hashable, Iterable, Iterator, Mapping, Optional, Tuple, TypeVar

	T = TypeVar("T")
	U = TypeVar("U")
	H = TypeVar("H", bound=Hashable)
	V = TypeVar("V")

def flatten(d):
	# type: (Dict[T, U], ) -> Iterator[U]

	""" Flattens dicts of (dicts of...) lists to lists. """

	if isinstance(d, (list, tuple)):
		for v in d:
			yield v
	elif isinstance(d, dict):
		for k, val in viewitems(d):
			for v in flatten(val):
				yield v
	else:
		raise TypeError("Unsupported type: {}".format(type(d)))

def get_one_of(d, keys):
	# type: (Dict[T, U], Iterable[T]) -> Tuple[T, U]

	""" Returns the (key, value) pair of the first key of `keys` found in `d`.
	"""

	for key in keys:
		try:
			return key, d[key]
		except KeyError:
			pass

	raise KeyError("None of the {} keys could be found".format(len(keys)))

def get_available(d, keys):
	# type: (Dict[T, U], Iterable[T]) -> Iterator[Tuple[T, U]]

	for key in keys:
		try:
			yield key, d[key]
		except KeyError:
			pass

def hasvalues(d):
	# type: (dict, ) -> dict

	return {k:v for k, v in viewitems(d) if v}

def valuemap(func, d):
	# type: (Callable[[U], V], Dict[T, U]) -> Dict[T, V]

	return {k: func(v) for k, v in viewitems(d)}

# was: mapdict, mapget
def mapmap(d, it):
	# type: (Mapping[T, U], Iterable[T]) -> Iterator[U]

	return (d[i] for i in it)

def itemgetter(it):
	# type: (Iterable[T], ) -> Callable[[Mapping[T, U]], Iterator[U]]

	""" Similar to `operator.itemgetter` except that it always expects and returns iterables.
		Compare `mapmap`
	"""

	return lambda d: (d[i] for i in it)

def subdict(d, it):
	# type: (Mapping[T, U], Iterable[T]) -> Dict[T, U]

	""" Uses the elements of `it` as keys to extract a new sub-dictionary. """

	return {key: d[key] for key in it}

def subdictdefault(d, it, default=None):
	# type: (Mapping[T, U], Iterable[T], Optional[T]) -> Dict[T, U]

	""" Uses the elements of `it` as keys to extract a new sub-dictionary. """

	return {key: d.get(key, default) for key in it}

def update(d1, d2):
	# type: (dict, dict) -> None

	""" Same as `dict.update` except that `None` values are skipped. """

	for k, v in viewitems(d2):
		if v is not None:
			d1[k] = v

class keydefaultdict(defaultdict):

	""" defaultdict which passes a key to the default factory. """

	def __missing__(self, key):
		# type: (Hashable, ) -> Any

		if self.default_factory is None:
			raise KeyError(key)
		else:
			value = self[key] = self.default_factory(key)
			return value
