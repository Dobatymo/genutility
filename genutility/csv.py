from __future__ import absolute_import, division, print_function, unicode_literals

from future.utils import PY2

import csv
from functools import partial
from io import open
from itertools import islice
from typing import TYPE_CHECKING

from .dict import itemgetter
from .func import compose, identity, zipmap

if TYPE_CHECKING:
	from typing import Callable, Iterator, List, Optional, Sequence

def iter_csv(path, delimiter=",", encoding="utf-8"):
	# type: (str, str, str, str, str) -> Iterator[List[str]]

	if PY2:
		with open(path, "rb") as fr:
			for data in csv.reader(fr, delimiter=delimiter.encode(encoding)):
				yield list(field.decode(encoding) for field in data)
	else:
		with open(path, "rt", encoding="utf-8", newline="") as fr:
			for data in csv.reader(fr, delimiter=delimiter):
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
