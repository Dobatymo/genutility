from __future__ import generator_stop

from typing import Any, Iterable, Optional, Sequence, TypeVar, Union

from typing_extensions import Protocol  # typing.Protocol is availalble in Python 3.8+

Number = Union[int, float]
T = TypeVar("T")


class Comparable(Protocol):
    def __eq__(self, other: Any) -> bool:
        ...

    def __ne__(self, other: Any) -> bool:
        ...


class Orderable(Protocol):
    def __lt__(self, other: Any) -> bool:
        ...

    def __gt__(self, other: Any) -> bool:
        ...

    def __le__(self, other: Any) -> bool:
        ...

    def __ge__(self, other: Any) -> bool:
        ...


class Computable(Protocol):
    def __neg__(self) -> Any:
        ...

    def __add__(self, other: Any) -> Any:
        ...

    def __sub__(self, other: Any) -> Any:
        ...

    def __mul__(self, other: Any) -> Any:
        ...

    def __truediv__(self, other: Any) -> Any:
        ...

    def __floordiv__(self, other: Any) -> Any:
        ...

    def __abs__(self) -> Any:
        ...


class MutableComputable(Protocol):
    def __neg__(self) -> Any:
        ...

    def __add__(self, other: Any) -> Any:
        ...

    def __iadd__(self, other: Any) -> Any:
        ...

    def __sub__(self, other: Any) -> Any:
        ...

    def __isub__(self, other: Any) -> Any:
        ...

    def __mul__(self, other: Any) -> Any:
        ...

    def __imul__(self, other: Any) -> Any:
        ...

    def __truediv__(self, other: Any) -> Any:
        ...

    def __itruediv__(self, other: Any) -> Any:
        ...

    def __floordiv__(self, other: Any) -> Any:
        ...

    def __ifloordiv__(self, other: Any) -> Any:
        ...


class Cursor(Protocol):
    def callproc(self, procname: str, parameters: Optional[Sequence[Any]]) -> None:
        ...

    def close(self) -> None:
        ...

    def execute(self, operation, parameters):
        # types: (str, Optional[Sequence[Any]]) -> None
        ...

    def executemany(self, operation, seq_of_parameters):
        # types: (str, Sequence[Sequence[Any]]) -> None
        ...

    def fetchone(self):
        # types: () -> Optional[Sequence[Any]]
        ...

    def fetchmany(self, size):
        # types: (Optional[int], ) -> Sequence[Sequence[Any]]
        ...

    def fetchall(self):
        # types: () -> Sequence[Sequence[Any]]
        ...

    def nextset(self) -> Optional[bool]:
        ...

    def setinputsizes(self, sizes):
        # types: (Sequence[int], ) -> None
        ...

    def setoutputsize(self, size: int, column: Optional[int]) -> None:
        ...


class Connection(Protocol):
    def close(self) -> None:
        ...

    def commit(self) -> None:
        ...

    def rollback(self) -> None:
        ...

    def cursor(self) -> Cursor:
        ...


class CsvWriter(Protocol):
    def writerow(self, row: Iterable[Any]) -> Any:
        ...

    def writerows(self, rows: Iterable[Iterable[Any]]) -> None:
        ...
