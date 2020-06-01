from __future__ import absolute_import, division, print_function, unicode_literals

from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from typing import Set, TypeVar
	T = TypeVar("T")

def get(s):
	# type: (Set[T], ) -> T

	for i in s:
		return i
