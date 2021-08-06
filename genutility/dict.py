from __future__ import generator_stop

from collections import UserDict, defaultdict
from typing import Any, Callable, Dict, Hashable, Iterable, Iterator, List, Mapping, Tuple, TypeVar, Union

T = TypeVar("T")
U = TypeVar("U")
V = TypeVar("V")

def flatten(d: Union[Dict[T, U], List[U], Tuple[U, ...]]) -> Iterator[U]:

	""" Flattens dicts/lists of (dicts/lists of ...) lists to lists. """

	if isinstance(d, (list, tuple)):
		for v in d:
			yield v
	elif isinstance(d, dict):
		for k, val in d.items():
			for v in flatten(val):
				yield v
	else:
		raise TypeError("Unsupported type: {}".format(type(d)))

def get_one_of(d: Dict[T, U], keys: Iterable[T]) -> Tuple[T, U]:

	""" Returns the (key, value) pair of the first key of `keys` found in `d`.
	"""

	for key in keys:
		try:
			return key, d[key]
		except KeyError:
			pass

	raise KeyError("None of the {} keys could be found".format(len(keys)))

# similar: subdict
def get_available(d: Dict[T, U], keys: Iterable[T]) -> Iterator[Tuple[T, U]]:

	""" Returns all the key-value pairs in `d` for the keys in `it`.
		Missing keys are ignored.
	"""

	for key in keys:
		try:
			yield key, d[key]
		except KeyError:
			pass

def subdict(d: Mapping[T, U], it: Iterable[T]) -> Dict[T, U]:

	""" Uses the elements of `it` as keys to extract a new sub-dictionary.
		Raises if not all keys in `it` are available.
	"""

	return {key: d[key] for key in it}

# was: mapdict, mapget
def mapmap(d: Mapping[T, U], it: Iterable[T]) -> Iterator[U]:
	""" Returns all the values of `d` for the keys in `it`.
		Raises for missing keys.
	"""

	return (d[i] for i in it)

def hasvalues(d: dict) -> dict:

	""" Returns a sub-dictionary which leaves out all pairs where the value evaluates to False.
	"""

	return {k: v for k, v in d.items() if v}

def valuemap(func: Callable[[U], V], d: Dict[T, U]) -> Dict[T, V]:

	""" Returns a new dictionary with `func` applied to all values of `d`.
	"""

	return {k: func(v) for k, v in d.items()}

def itemgetter(it: Iterable[T]) -> Callable[[Mapping[T, U]], Iterator[U]]:

	""" Similar to `operator.itemgetter` except that it always expects and returns iterables.
		Compare `mapmap`
	"""

	return lambda d: (d[i] for i in it)

def subdictdefault(d, it, default=None):
	# type: (Mapping[T, U], Iterable[T], Union[U, V]) -> Dict[T, Union[U, V]]

	""" Uses the elements of `it` as keys to extract a new sub-dictionary. """

	return {key: d.get(key, default) for key in it}

def update(d1: dict, d2: dict) -> None:

	""" Same as `dict.update` except that `None` values are skipped. """

	for k, v in d2.items():
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


class KeyExistsError(KeyError):
	pass


class NoOverwriteDict(UserDict):

	""" Dictionary which does not allow overwriting existing items.
	"""

	def __setitem__(self, key, value):
		if key in self.data:
			raise KeyExistsError(repr(key))
		self.data[key] = value

	def overwrite(self, key, value):
		self.data[key] = value
