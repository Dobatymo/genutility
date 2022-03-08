from __future__ import generator_stop

import csv
from functools import partial
from itertools import islice
from typing import Callable, Iterator, List, Optional, Sequence

from .dict import itemgetter
from .func import compose, identity, zipmap


def iter_csv(path: str, delimiter: str = ",", encoding: str = "utf-8", skip: int = 0) -> Iterator[List[str]]:

    with open(path, encoding="utf-8", newline="") as fr:
        yield from islice(csv.reader(fr, delimiter=delimiter), skip, None)


def read_csv(
    path: str,
    delimiter: str = ",",
    skip: int = 0,
    usecols: Optional[Sequence[int]] = None,
    dtype: Optional[Sequence[Callable]] = None,
    encoding: str = "utf-8",
) -> Iterator[tuple]:

    with open(path, encoding=encoding, newline="") as csvfile:
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
