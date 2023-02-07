from enum import Enum
from typing import Callable, Optional, Sequence, TypeVar

from .func import identity

T = TypeVar("T")
U = TypeVar("U")


class BisectRetVal(Enum):
    Lower = -1
    Equal = 0
    Higher = 1


def make_binary_search(target: int) -> Callable[[int], BisectRetVal]:
    def binary_search_func(x):
        if x < target:
            return BisectRetVal.Higher
        elif x > target:
            return BisectRetVal.Lower
        else:
            return BisectRetVal.Equal

    return binary_search_func


def make_binary_search_sequence(
    seq: Sequence[T], target: U, key: Optional[Callable[[T], U]] = None
) -> Callable[[int], BisectRetVal]:
    _key = key or identity

    def binary_search_func(x: int) -> BisectRetVal:
        result = _key(seq[x])
        if result < target:
            return BisectRetVal.Higher
        elif result > target:
            return BisectRetVal.Lower
        else:
            return BisectRetVal.Equal

    return binary_search_func


def bisect_left_generic(lo: int, hi: int, func: Callable[[int], BisectRetVal]) -> int:
    """Generic left bisection (binary search). Finds a specific `lo<=x<=hi` where
    `func(x) == BisectRetVal.Equal` or where the return value changes from BisectRetVal.Higher
    to `BisectRetVal.Lower`.
    """

    while lo < hi:
        mid = (lo + hi) // 2
        result = func(mid)
        if result == BisectRetVal.Higher:
            lo = mid + 1
        else:
            hi = mid
    return lo


def bisect_right_generic(lo: int, hi: int, func: Callable[[int], BisectRetVal]) -> int:
    """Generic right bisection (binary search). Finds a specific `lo<=x<=hi` where
    `func(x) == BisectRetVal.Equal` or where the return value changes from BisectRetVal.Higher
    to `BisectRetVal.Lower`.
    """

    while lo < hi:
        mid = (lo + hi) // 2
        result = func(mid)
        if result == BisectRetVal.Lower:
            hi = mid
        else:
            lo = mid + 1
    return lo


def bisect_left_sequence(seq: Sequence[T], target, key=None) -> int:
    """see: bisect.bisect_left"""

    func = make_binary_search_sequence(seq, target, key)
    return bisect_left_generic(0, len(seq), func)


def bisect_right_sequence(seq: Sequence[T], target, key=None) -> int:
    """see: bisect.bisect_right"""

    func = make_binary_search_sequence(seq, target, key)
    return bisect_right_generic(0, len(seq), func)


def search_sorted(seq: Sequence[T], newitem: U, key: Optional[Callable[[T], U]] = None) -> int:
    _key = key or identity

    for i, item in enumerate(seq):
        if newitem < _key(item):
            return i

    return len(seq)


if __name__ == "__main__":
    seq = [1, 2, 3, 4, 4, 5]
    from bisect import bisect_left, bisect_right

    for target in (1, 2, 3, 4, 5, 0.5, 1.5, 2.5, 3.5, 4.5, 5.5):
        print(bisect_left_sequence(seq, target) == bisect_left(seq, target))
        print(search_sorted(seq, target) == bisect_right_sequence(seq, target) == bisect_right(seq, target))
