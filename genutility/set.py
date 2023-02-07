from typing import Set, TypeVar

T = TypeVar("T")


def get(s: Set[T]) -> T:
    for i in s:
        return i

    raise KeyError("set empty")
