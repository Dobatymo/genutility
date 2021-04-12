from __future__ import generator_stop

import csv
from functools import partial
from itertools import islice
from typing import Callable, Iterator, List, Optional, Sequence

from .dict import itemgetter
from .func import compose, identity, zipmap


def iter_csv(path, delimiter=",", encoding="utf-8", skip=0):
	# type: (str, str, str, bool) -> Iterator[List[str]]

	with open(path, "rt", encoding="utf-8", newline="") as fr:
		for data in islice(csv.reader(fr, delimiter=delimiter), skip, None):
			yield data

def read_csv(path, delimiter=",", skip=0, usecols=None, dtype=None, encoding="utf-8"):
	# type: (str, str, int, Optional[Sequence[int]], Optional[Sequence[Callable]], str) -> Iterator[tuple]

	with open(path, "rt", encoding=encoding, newline="") as csvfile:
		if usecols:
			if dtype:
				getcols = compose(partial(zipmap, dtype), itemgetter(usecols))
			else:
				getcols = itemgetter(usecols)
		else:
			if dtype:
				getcols = partial(zipmap, dtype)
			else:
				getcols = identity

		for row in islice(csv.reader(csvfile, delimiter=delimiter), skip, None):
			print(row)
			yield tuple(getcols(row))
