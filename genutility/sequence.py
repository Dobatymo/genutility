from operator import itemgetter
from typing import Callable, Dict, Iterator, MutableSequence, Optional, Sequence, Tuple, TypeVar

from .func import identity
from .indexing import triangular_indices
from .typing import Comparable, Orderable

T = TypeVar("T")


class LazyStringList:
    def __init__(self, length: int) -> None:
        self.length = length

    def __getitem__(self, idx: int) -> str:
        return str(idx)

    def __len__(self) -> int:
        return self.length

    def __iter__(self) -> Iterator[str]:
        return map(str, range(self.length))

    def __contains__(self, idx: int) -> bool:
        return 0 <= idx < self.length


def pop_many(seq: MutableSequence[T], func: Callable) -> Iterator[T]:
    """`pop()`s values from `seq` where func(value) is true.
    For performance reasons the elements are popped
    and yielded in reverse order.
    """

    idx = [i for i, elm in enumerate(seq) if func(elm)]

    for i in reversed(idx):
        yield seq.pop(i)


def triangular(seq: Sequence[T]) -> Iterator[Tuple[T, T]]:
    """Returns all combinations of items of `seq` with duplicates and self-combinations.
    triangular([1, 2, 3, 4]) -> (1, 2), (1, 3), (1, 4), (2, 3), (2, 4), (3, 4)
    """

    for i, j in triangular_indices(len(seq)):
        yield seq[i], seq[j]


def sliding_window(seq: Sequence[T], size: int, step: int = 1) -> Iterator[Sequence[T]]:
    """Similar to `iter.x_wise()` except that it returns slices of a sequence.
    sliding_window([1, 2, 3], 2) -> [1, 2], [2, 3]
    sliding_window([1, 2, 3, 4, 5], 2, 3) -> [1, 2], [4, 5]
    """

    seqlen = len(seq)
    if size > seqlen:
        raise ValueError("size must be less or equal the length of the sequence")

    for i in range(0, seqlen - size + 1, step):
        yield seq[i : i + size]


def batch(seq: Sequence[T], size: int) -> Iterator[Sequence[T]]:
    """Similar to `iter.batch()` except that it returns slices of a sequence.
    batch([1, 2, 3], 2) -> [1, 2], [3]
    batch([1, 2, 3, 4, 5], 3) -> [1, 2, 3], [4, 5]
    """

    if size < 1:
        raise ValueError("size must be larger than 0")

    seqlen = len(seq)

    for i in range(0, (seqlen + size - 1) // size):
        yield seq[i * size : (i + 1) * size]


def delete_duplicates_from_sorted_sequence(
    seq: MutableSequence[T], key: Optional[Callable[[T], Comparable]] = None
) -> None:
    """Deletes duplicates from a sorted sequence `seq` based on `key`.
    Works in-place.
    """

    key = key or identity
    i = 0
    while i < len(seq) - 1:
        if key(seq[i]) == key(seq[i + 1]):
            del seq[i + 1]
        else:
            i += 1


def remove_duplicate_rows_from_sorted_table(seq: MutableSequence[Dict[str, T]], key: str) -> None:
    return delete_duplicates_from_sorted_sequence(seq, itemgetter(key))


def cycle_sort(seq: MutableSequence[Orderable]) -> Iterator[Tuple[int, int]]:
    """Sort a sequence in place and yield swaps.
    based on: https://rosettacode.org/wiki/Sorting_algorithms/Cycle_sort#Python
    """

    # Loop through the sequence to find cycles to rotate.
    for cycle_start, item in enumerate(seq):
        # Find where to put the item.
        pos = cycle_start
        for item2 in seq[cycle_start + 1 :]:
            if item2 < item:
                pos += 1

        # If the item is already there, this is not a cycle.
        if pos == cycle_start:
            continue

        # Otherwise, put the item there or right after any duplicates.
        while item == seq[pos]:
            pos += 1
        seq[pos], item = item, seq[pos]
        yield cycle_start, pos

        # Rotate the rest of the cycle.
        while pos != cycle_start:
            # Find where to put the item.
            pos = cycle_start
            for item2 in seq[cycle_start + 1 :]:
                if item2 < item:
                    pos += 1

            # Put the item there or right after any duplicates.
            while item == seq[pos]:
                pos += 1
            seq[pos], item = item, seq[pos]
            if pos != cycle_start:
                yield cycle_start, pos
