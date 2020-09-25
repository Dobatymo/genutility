from __future__ import absolute_import, division, print_function, unicode_literals

from collections.abc import Iterable, Sized
from typing import TYPE_CHECKING


class SizedIterable(Iterable, Sized):
	pass

if TYPE_CHECKING:

	from typing import Any, Optional, Sequence, Union

	from typing_extensions import Protocol

	Number = Union[int, float]

	class Comparable(Protocol):

		def __eq__(self, other):
			# type: (Any, ) -> bool
			...

		def __ne__(self, other):
			# type: (Any, ) -> bool
			...

	class Orderable(Protocol):

		def __lt__(self, other):
			# type: (Any, ) -> bool
			...

		def __gt__(self, other):
			# type: (Any, ) -> bool
			...

		def __le__(self, other):
			# type: (Any, ) -> bool
			...

		def __ge__(self, other):
			# type: (Any, ) -> bool
			...

	class Computable(Protocol):

		def __neg__(self, other):
			# type: (Any, ) -> Any
			...

		def __add__(self, other):
			# type: (Any, ) -> Any
			...

		def __sub__(self, other):
			# type: (Any, ) -> Any
			...

		def __mul__(self, other):
			# type: (Any, ) -> Any
			...

		def __truediv__(self, other):
			# type: (Any, ) -> Any
			...

		def __floordiv__(self, other):
			# type: (Any, ) -> Any
			...

		def __abs__(self, other):
			# type: (Any, ) -> Any
			...

	class MutableComputable(Protocol):

		def __neg__(self, other):
			# type: (Any, ) -> Any
			...

		def __add__(self, other):
			# type: (Any, ) -> Any
			...

		def __iadd__(self, other):
			# type: (Any, ) -> Any
			...

		def __sub__(self, other):
			# type: (Any, ) -> Any
			...

		def __isub__(self, other):
			# type: (Any, ) -> Any
			...

		def __mul__(self, other):
			# type: (Any, ) -> Any
			...

		def __imul__(self, other):
			# type: (Any, ) -> Any
			...

		def __truediv__(self, other):
			# type: (Any, ) -> Any
			...

		def __itruediv__(self, other):
			# type: (Any, ) -> Any
			...

		def __floordiv__(self, other):
			# type: (Any, ) -> Any
			...

		def __ifloordiv__(self, other):
			# type: (Any, ) -> Any
			...

	class Cursor(Protocol):

		def callproc(self, procname, parameters):
			# type: (str, Optional[Sequence[Any]]) -> None
			...

		def close(self):
			# type: () -> None
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

		def nextset(self):
			# type: () -> Optional[bool]
			...

		def setinputsizes(self, sizes):
			# types: (Sequence[int], ) -> None
			...

		def setoutputsize(self, size, column):
			# type: (int, Optional[int]) -> None
			...

	class Connection(Protocol):

		def close(self):
			# type: () -> None
			...

		def commit(self):
			# type: () -> None
			...

		def rollback(self):
			# type: () -> None
			...

		def cursor(self):
			# type: () -> Cursor
			...
