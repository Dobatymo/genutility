from __future__ import absolute_import, division, print_function, unicode_literals

from typing import TYPE_CHECKING

if TYPE_CHECKING:

	from typing import Any
	from typing_extensions import Protocol

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
