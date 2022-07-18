from __future__ import generator_stop

from random import choice, randrange, sample
from typing import Iterator, Sequence, Tuple


def randstr(length: int, charset: str) -> str:

    """Returns a (noncryptographic) random string consisting of characters from `charset`
    of length `length`.
    """

    return "".join(choice(charset) for i in range(length))  # nosec


def randbytes(size: int) -> bytes:

    """Returns (noncryptographic) random bytes of length `length`."""

    return bytes(randrange(0, 256) for _ in range(size))  # nosec


def rgb_colors():
    # type: () -> Iterator[Tuple[int, int, int]]

    """Yields a stream of (noncryptographic) random RGB color tuples."""

    while True:
        rgb = randrange(0, 256**3)  # nosec
        rg, b = divmod(rgb, 256)
        r, g = divmod(rg, 256)
        yield (r, g, b)


def randomized(seq: Sequence) -> Sequence:

    """Like `random.shuffle`, but not in-place."""

    return sample(seq, len(seq))
