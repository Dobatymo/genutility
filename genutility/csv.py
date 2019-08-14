from __future__ import absolute_import, division, print_function, unicode_literals

import csv
from itertools import islice
from functools import partial

from .dict import itemgetter
from .func import identity, zipmap, compose

def read_csv(path, delimiter=",", skip=0, usecols=None, dtype=None):
	with open(path, encoding="utf-8", newline="") as csvfile:
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
