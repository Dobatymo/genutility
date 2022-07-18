from __future__ import generator_stop

import heapq
import os
from collections.abc import Iterable
from contextlib import ExitStack
from itertools import islice
from operator import itemgetter
from typing import Any, AnyStr, Callable, Generic
from typing import Iterable as IterableT
from typing import Iterator, List, MutableSequence, Optional, Tuple, TypeVar, Union

from .file import copen
from .func import identity
from .math import argmax, argmin

T = TypeVar("T")
U = TypeVar("U")


def bubble_sort(seq: MutableSequence) -> None:

    """Slightly optimized version of stable bubble sort. Sorts input `seq` in place."""

    n = len(seq)
    while True:
        newn = 1
        for i in range(1, n):
            if seq[i - 1] > seq[i]:
                seq[i - 1], seq[i] = seq[i], seq[i - 1]
                newn = i
        if newn == 1:
            break
        n = newn


def selection_sort_min(seq: MutableSequence) -> None:
    # inplace, unstable

    n = len(seq)
    for i in range(n - 1):
        m = argmin(seq, i, n)
        if m != i:
            seq[i], seq[m] = seq[m], seq[i]


def selection_sort_max(seq: MutableSequence) -> None:
    # inplace, unstable

    for n in range(len(seq) - 1, 0, -1):
        m = argmax(seq[: n + 1])
        if m != n:
            seq[m], seq[n] = seq[n], seq[m]


def selection_sort_ll(seq):
    # inplace, stable, on linked lists
    raise NotImplementedError


class OptionalValue(Generic[T]):
    def __init__(self, value: T) -> None:
        self.value = value

    def __repr__(self) -> str:
        return "<Optional " + repr(self.value) + ">"

    def __eq__(self, other: "OptionalValue[T]") -> bool:
        return self.value == other.value

    def __lt__(self, other: "OptionalValue[T]") -> bool:

        a = self.value
        b = other.value

        if a is None:
            return True
        if b is None:
            return False

        if not isinstance(a, str) and isinstance(a, Iterable):
            a = tuple(map(OptionalValue, a))
        if not isinstance(b, str) and isinstance(b, Iterable):
            b = tuple(map(OptionalValue, b))

        return a < b


def sorted_index(it: IterableT[T], reverse: bool = False) -> Iterator[Tuple[T, int]]:

    """adds the position of each element after sorting without changing the order of the elements
    eg. [2, 6, -1, 4] -> [(2, 2), (6, 4), (-1, 1), (4, 3)]
    """

    return (
        (x[1][1], x[0])
        for x in sorted(enumerate(sorted(enumerate(it), key=lambda x: x[1], reverse=reverse), 1), key=lambda x: x[1][0])
    )


def sorted_by_list(
    tosort: IterableT[T], sortby: IterableT[U], reverse: bool = False, include_keys: bool = False
) -> Union[IterableT[Tuple[T, U]], Iterator[T]]:

    """Sorts `tosort` using the elements of `sortby`.
    The length of the shorter of both list determines the length of the output.
    eg. [1,2,3,4], [2,4,1,3] -> [3,1,4,2] for include_keys is False
    """

    ret = sorted(zip(tosort, sortby), key=itemgetter(1), reverse=reverse)
    if not include_keys:
        return map(itemgetter(0), ret)
    else:
        return ret


def sorted_with_keys(it: IterableT[T], key: Callable[[T], U], reverse: bool = False) -> Iterator[Tuple[T, U]]:

    """Sorts `it` using function `key` adds keys to output.
    eg. [2,4,1,3], lambda x: -x -> [(4,-4),(3,-3),(2,-2),(1,-1)]
    """

    with_keys = ((elm, key(elm)) for elm in it)
    return sorted(with_keys, key=itemgetter(1), reverse=reverse)


def external_sort(
    in_iterator: IterableT[AnyStr],
    temp_file_template: str,
    mode: str = "t",
    key: Optional[Callable[[str], Any]] = None,
    max_lines_temp: Optional[int] = None,
    max_lines_final: Optional[int] = None,
) -> Iterator[AnyStr]:

    """Sorts `in_iterator` by using external files. Keeps at most `max_lines_temp` lines in memory at any time.
    `in_iterator` must not yield any newlines. They must be escaped beforehand.
    If mode is "t" `in_iterator` must yield `str`, mode "b" it must yield `bytes`.
    `max_lines_final` limits output size. `key` is the key function for `sort()`.
    """

    # doesn't handle newlines in input correctly

    assert mode in {"t", "b"}

    if mode == "t":
        encoding: Optional[str] = "utf-8"
        errors: Optional[str] = "strict"
        newline: AnyStr = "\n"
    else:
        encoding = None
        errors = None
        newline = b"\n"

    if key is None:
        key = identity

    if max_lines_temp is None:
        # find some clever way to do that, based on memory and so on.
        max_lines_temp = 10000000

    def file_write_iter(path, it):
        with copen(path, "w" + mode, compresslevel=1, encoding=encoding, errors=errors, newline=newline) as fw:
            for line in it:
                fw.write(line + newline)

    # create temp files, write sequentially

    file_count = 0
    lines: List[AnyStr] = []

    for line in in_iterator:
        lines.append(line.rstrip(newline))  # removes newlines from input
        if len(lines) >= max_lines_temp:
            lines.sort(key=key)
            file_write_iter(temp_file_template.format(file_count), lines)
            file_count += 1
            lines = []
    if lines:
        lines.sort(key=key)
        file_write_iter(temp_file_template.format(file_count), lines)
        file_count += 1
        lines = []

    # merge temp files, read parallel

    filenames = [temp_file_template.format(i) for i in range(file_count)]
    with ExitStack() as stack:
        files = [
            stack.enter_context(copen(name, "r" + mode, encoding=encoding, errors=errors, newline=newline))
            for name in filenames
        ]

        merged = heapq.merge(*files, key=key)

        for line in islice(merged, max_lines_final):
            yield line.rstrip(newline)

    # remove temp files

    for name in filenames:
        os.remove(name)


def external_sort_file(
    in_file: str,
    out_file: str,
    temp_file_template: str,
    sort_key: Optional[Callable[[str], Any]] = None,
    max_lines_temp: Optional[int] = None,
    max_lines_final: Optional[int] = None,
) -> None:

    """Sorts file `in_file` to `out_file` line by line using external files
    provided by filename `template temp_file_template`.
    At most `max_lines_temp` lines will be in memory at any time.
    """

    with copen(in_file, "rt", encoding="utf-8", errors="strict") as fr, copen(
        out_file, "wt", encoding="utf-8", errors="strict", newline="\n"
    ) as fw:
        lines = external_sort(fr, temp_file_template, "t", sort_key, max_lines_temp, max_lines_final)

        fw.writelines(map(lambda s: s + "\n", lines))
