from collections.abc import MutableMapping
from typing import AbstractSet, Iterator, List, Tuple, TypeVar, cast

T = TypeVar("T")


class VariableRowMatrixItems(AbstractSet[Tuple[Tuple[int, int], T]]):
    def __init__(self, vrm):
        self.vrm = vrm

    def __iter__(self) -> Iterator[Tuple[Tuple[int, int], T]]:
        for r, row in enumerate(self.vrm.lol):
            for c, value in enumerate(row):
                yield (r, c), value

    def __len__(self) -> int:
        return sum(len(row) for row in self.vrm.lol)

    def __contains__(self, key: object) -> bool:
        (i, j), value = cast(Tuple[Tuple[int, int], T], key)

        return self.vrm.lol[i][j] == value


class VariableRowMatrix(MutableMapping[Tuple[int, int], T]):
    def __init__(self, default: T) -> None:
        self.lol: List[List[T]] = []
        self.default = default

    @classmethod
    def from_list_of_lists(cls, lol: List[List[T]]) -> "VariableRowMatrix[T]":
        m = VariableRowMatrix.__new__(cls)
        m.lol = lol
        return m

    def __len__(self) -> int:
        return len(self.lol)

    def __iter__(self) -> Iterator[Tuple[int, int]]:
        for r, row in enumerate(self.lol):
            for c, _value in enumerate(row):
                yield (r, c)

    def items(self) -> VariableRowMatrixItems[T]:
        return VariableRowMatrixItems(self)

    def __setitem__(self, key: Tuple[int, int], value: T) -> None:
        i, j = key

        try:
            row = self.lol[i]
        except IndexError:
            mul = i - len(self.lol) + 1
            tmp: List[List[T]] = [[]]
            self.lol.extend(mul * tmp)
            row = self.lol[i]

        try:
            row[j] = value
        except IndexError:
            mul = j - len(row) + 1
            row.extend(mul * [self.default])
            row[j] = value

    def __delitem__(self, key: Tuple[int, int]) -> None:
        """del vrm[i, j] only sets the the value to 0"""

        i, j = key
        self.lol[i][j] = self.default

    def __getitem__(self, key: Tuple[int, int]) -> T:
        i, j = key
        return self.lol[i][j]
