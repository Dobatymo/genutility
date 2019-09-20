from __future__ import absolute_import, division, print_function, unicode_literals

from future.utils import viewitems
from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from typing import Any, Callable, Dict, Hashable, Iterable, Mapping, Optional

	T = TypeVar("T")
	U = TypeVar("U")
	H = TypeVar("H", bound=Hashable)

def hasvalues(d):
	return {k:v for k, v in viewitems(d) if v}

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

class keydefaultdict(defaultdict):

	""" defaultdict which passes a key to the default factory. """

	def __missing__(self, key):
		# type: (Hashable, ) -> Any

		if self.default_factory is None:
			raise KeyError(key)
		else:
			value = self[key] = self.default_factory(key)
			return value
