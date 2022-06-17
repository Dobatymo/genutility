from __future__ import generator_stop

from itertools import cycle
from typing import Iterable, Iterator


def xor_stream(it: Iterable[bytes], key: Iterable[bytes], cyclekey: bool = True) -> Iterator[bytes]:

    if cyclekey:
        key = cycle(key)

    for i, j in zip(it, key):
        yield bytes([i ^ j])
