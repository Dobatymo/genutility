from __future__ import generator_stop

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Set, TypeVar

    T = TypeVar("T")


def get(s):
    # type: (Set[T], ) -> T

    for i in s:
        return i

    raise KeyError("set empty")
