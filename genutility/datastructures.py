from __future__ import absolute_import, division, print_function, unicode_literals

from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from typing import List

	from .typing import Number

class VariableRowMatrix(object):

	def __init__(self):
		# type: () -> None

		self.lol = []

	@classmethod
	def from_list_of_lists(cls, lol):
		# type: (List[List[Number]], ) -> VariableRowMatrix

		m = VariableRowMatrix.__new__(cls)
		m.lol = lol
		return m

	def __len__(self):
		# type: () -> int

		return len(self.lol)

	def __setitem__(self, key, value):
		i, j = key

		try:
			row = self.lol[i]
		except IndexError:
			mul = i - len(self.lol) + 1
			self.lol.extend(mul*[[]])
			row = self.lol[i]

		try:
			row[j] = value
		except IndexError:
			mul = j - len(row) + 1
			row.extend(mul*[0])
			row[j] = value

	def __getitem__(self, key):
		i, j = key
		return self.lol[i][j]
