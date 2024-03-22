from random import choice, random, randrange, sample
from typing import Iterator, Sequence, Tuple


def randstr(length: int, charset: str) -> str:
    """Returns a (noncryptographic) random string consisting of characters from `charset`
    of length `length`.
    """

    return "".join(choice(charset) for i in range(length))  # nosec


def randbytes(size: int) -> bytes:
    """Returns (noncryptographic) random bytes of length `length`."""

    return bytes(randrange(0, 256) for _ in range(size))  # nosec


def rgb_colors() -> Iterator[Tuple[int, int, int]]:
    """Yields a stream of (noncryptographic) random RGB color tuples."""

    while True:
        rgb = randrange(0, 256**3)  # nosec
        rg, b = divmod(rgb, 256)
        r, g = divmod(rg, 256)
        yield (r, g, b)


def randomized(seq: Sequence) -> Sequence:
    """Like `random.shuffle`, but not in-place."""

    return sample(seq, len(seq))


def prob_false(probability: float) -> bool:
    """Returns `False` with a probability of `probability`."""

    if probability in (0, 1):
        return not bool(probability)  # for weird open interval edge cases

    return probability < random()  # random() -> [0.0, 1.0) # nosec
