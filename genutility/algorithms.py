from __future__ import generator_stop

from typing import Callable, MutableSequence, Optional, TypeVar

T = TypeVar("T")


def _insertion(seq: MutableSequence, cmp_: Callable, left: int, right: int, gap: int) -> None:

    loc = left + gap
    while loc <= right:
        i = loc - gap
        value = seq[loc]
        while i >= left and cmp_(seq[i], value) > 0:
            seq[i + gap] = seq[i]
            i -= gap
        seq[i + gap] = value
        loc += gap


GROUP_SIZE = 5


def cmp(x: T, y: T) -> int:

    """
    Return negative if x<y, zero if x==y, positive if x>y.
    """
    return (x > y) - (x < y)


def median_of_medians(
    seq: MutableSequence, cmp_: Optional[Callable] = None, left: int = 0, right: Optional[int] = None, depth: int = 0
) -> int:

    """Approximate median selection algorithm.
    This is not the full median of medians algorithm.
    Currently only works for len(seq) == GROUP_SIZE ** x
    """

    offset = (GROUP_SIZE ** (depth + 1) - GROUP_SIZE**depth) // 2

    gap = GROUP_SIZE**depth

    cmp_ = cmp_ or cmp

    if not right:
        right = len(seq) - 1

    span = GROUP_SIZE * gap
    num = (right - left + 1) // span

    if num == 0:
        _insertion(seq, cmp_, left, right, gap)
        num = (right - left + 1) // gap
        return left + gap * (num - 1) // 2  # select median

    s = left
    while s < right:
        _insertion(seq, cmp_, s, s + span - 1, gap)
        s += span

    if num < GROUP_SIZE:
        _insertion(seq, cmp_, left + offset, right, span)
        return left + offset + num * span // 2  # select median
    else:
        return median_of_medians(seq, cmp_, left + offset, right, depth + 1)
