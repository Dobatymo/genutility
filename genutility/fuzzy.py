from __future__ import absolute_import, division, print_function, unicode_literals

from heapq import nsmallest
from operator import itemgetter
from typing import TYPE_CHECKING

try:
	from polyleven import levenshtein as levenshtein_distance
except ImportError:
	from Levenshtein import distance as _distance

	def levenshtein_distance(s1, s2, max_distance):
		return _distance(s1, s2)

if TYPE_CHECKING:
	from typing import Callable, List, Iterable, Tuple

def preprocess(s):
	return s.replace(" ", "").lower()

def limitedsort(it, limit):
	# type: (Iterable[tuple], int) -> List[tuple]

	if limit < 0:
		return sorted(it, key=itemgetter(1))
	elif limit == 0:
		return []
	elif limit == 1:
		try:
			return [min(it, key=itemgetter(1))]
		except ValueError:
			return []
	else:
		return nsmallest(limit, it, key=itemgetter(1))

def distances(query, choices, distance_func, max_distance, preprocess_func):
	# type: (str, Iterable[str], Callable[[str, str, int], int], int, Callable[[str], str]) -> Iterator[Tuple[str, int]]

	query = preprocess_func(query)

	for choice in choices:
		score = distance_func(query, preprocess_func(choice), max_distance)
		if max_distance < 0 or score <= max_distance:
			yield choice, score

def extract(query, choices, max_distance=-1, limit=-1, distance_func=levenshtein_distance, preprocess_func=preprocess):
	# type: (str, Iterable[str], int, int, Callable[[str, str, int], int], Callable[[str], str]) -> List[Tuple[str, int]]

	return limitedsort(distances(query, choices, distance_func, max_distance, preprocess_func), limit)
