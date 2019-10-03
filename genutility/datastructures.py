from __future__ import absolute_import, division, print_function, unicode_literals

class VariableRowMatrix(object):

	def __init__(self):
		self.lol = []

	@classmethod
	def from_list_of_lists(cls, lol):
		# type: (List[List[Number]], ) -> VariableRowMatrix
		m = VariableRowMatrix.__new__(cls)
		m.lol = lol
		return m

	def __len__(self):
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

def benchmark(num=9999999, height=1000, width=100):

	import numpy as np
	from genutility.time import PrintStatementTime

	lol = np.arange(height*width).reshape((height, width)).tolist()
	d = dict()
	for i, col in enumerate(lol):
		for j, val in enumerate(col):
			d[i, j] = val

	sm = VariableRowMatrix.from_list_of_lists(lol)

	def index_lol():
		for x, y in zip(xs, ys):
			a = lol[x][y]

	def index_sm():
		for x, y in zip(xs, ys):
			a = sm[x, y]

	def index_sm_2():
		for ind in zip(xs, ys):
			a = sm[ind]

	def index_d():
		for x, y in zip(xs, ys):
			a = d[x, y]

	def index_d_2():
		for ind in zip(xs, ys):
			a = d[ind]

	xs = np.random.randint(0, height, num)
	ys = np.random.randint(0, width, num)

	for i in range(3):
		with PrintStatementTime("list of lists: {delta}"):
			index_lol()
		with PrintStatementTime("VariableRowMatrix: {delta}"):
			index_sm()
		with PrintStatementTime("VariableRowMatrix: {delta}"):
			index_sm_2()
		with PrintStatementTime("dict with tuple key: {delta}"):
			index_d()
		with PrintStatementTime("dict with single key: {delta}"):
			index_d_2()

if __name__ == "__main__":
	benchmark()
