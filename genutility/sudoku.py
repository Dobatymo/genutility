from __future__ import absolute_import, division, print_function, unicode_literals

from builtins import range
from copy import deepcopy

from .compat.math import isqrt
from .indexing import row_indices, col_indices, subblock_indices
from .set import get as setget

class Unsolvable(Exception):
	pass

sudokus = {
	"very_easy": [
		5,4,2,0,1,7,0,9,8,
		9,6,8,5,4,2,0,0,7,
		7,0,1,6,9,8,2,5,0,
		8,5,7,4,2,9,1,6,0,
		1,2,3,8,7,6,9,0,5,
		6,9,4,1,0,3,0,7,2,
		4,1,0,2,0,5,7,0,9,
		3,8,0,7,6,4,5,2,0,
		2,0,5,9,3,1,4,8,6
	],

	"easy": [
		4,8,5,1,0,6,9,0,0,
		6,2,0,0,9,0,8,0,0,
		0,1,0,2,0,8,0,7,0,
		8,6,4,3,0,0,7,0,9,
		2,0,0,9,0,5,0,0,4,
		5,9,1,4,0,7,0,2,8,
		0,4,8,0,5,9,2,6,3,
		0,5,2,0,3,4,1,8,7,
		0,0,6,8,0,1,4,0,5
	],

	"normal": [
		5,0,1,3,4,2,0,0,0,
		0,0,2,0,1,0,0,5,3,
		3,0,7,5,0,0,0,0,0,
		9,0,8,0,0,3,0,4,1,
		0,0,0,0,9,0,0,0,0,
		1,4,0,2,7,0,5,0,6,
		0,0,0,0,2,4,8,0,9,
		7,1,4,0,6,0,3,0,0,
		0,0,0,0,3,0,0,0,4
	],

	"hard": [
		0,2,0,0,6,5,0,0,3,
		0,0,3,0,8,0,2,0,1,
		4,0,0,0,0,0,0,0,0,
		0,9,0,0,1,6,4,7,0,
		0,0,1,0,0,0,6,0,0,
		0,4,5,7,3,0,0,9,0,
		0,0,0,0,0,0,0,0,4,
		2,0,8,0,4,0,3,0,0,
		1,0,0,5,9,0,0,2,0
	],

	"very": [
		2,8,5,0,0,0,0,0,0,
		0,7,0,0,2,5,0,0,9,
		0,0,0,0,0,0,0,0,4,
		1,9,0,0,0,0,0,0,0,
		6,0,0,0,9,0,0,1,0,
		0,0,0,7,0,4,0,8,0,
		0,0,0,8,0,3,0,0,0,
		0,0,3,6,0,0,0,4,0,
		0,0,0,0,0,0,5,0,0
	],

	"suck": [
		0,0,5,3,0,0,0,0,0,
		8,0,0,0,0,0,0,2,0,
		0,7,0,0,1,0,5,0,0,
		4,0,0,0,0,5,3,0,0,
		0,1,0,0,7,0,0,0,6,
		0,0,3,2,0,0,0,8,0,
		0,6,0,5,0,0,0,0,9,
		0,0,4,0,0,0,0,3,0,
		0,0,0,0,0,9,7,0,0
	],

	"Arto_Inkala": [
		8,0,0,0,0,0,0,0,0,
		0,0,3,6,0,0,0,0,0,
		0,7,0,0,9,0,2,0,0,
		0,5,0,0,0,7,0,0,0,
		0,0,0,0,4,5,7,0,0,
		0,0,0,1,0,0,0,3,0,
		0,0,1,0,0,0,0,6,8,
		0,0,8,5,0,0,0,1,0,
		0,9,0,0,0,0,4,0,0
	],
	
	"norvig": [# unsolvable, doesn't have a solution
		0,0,0,0,0,5,0,8,0,
		0,0,0,6,0,1,0,4,3,
		0,0,0,0,0,0,0,0,0,
		0,1,0,5,0,0,0,0,0,
		0,0,0,1,0,6,0,0,0,
		3,0,0,0,0,0,0,0,5,
		5,3,0,0,0,0,0,6,1,
		0,0,0,0,0,0,0,0,4,
		0,0,0,0,0,0,0,0,0
	],
}

class Sudoku(object):

	def __init__(self, outer_square_size, square, sym_set, sym_free):
		assert isinstance(sym_set, set)

		self.outer_square_size = outer_square_size
		self.outer_square_area = self.outer_square_size * self.outer_square_size
		self.inner_square_size = isqrt(outer_square_size)
		if self.inner_square_size ** 2 != self.outer_square_size:
			raise ArithmeticError("outer_square_size is not a multiple of inner_square_size")
		self.square = square
		if len(self.square) != self.outer_square_area:
			raise ArithmeticError("elements in list != sudoku size")

		self.solved = False
		self.sym_set = sym_set
		self.sym_free = sym_free

	def init_square(self, sudoku):
		raise NotImplementedError

	def get_square(self):
		raise NotImplementedError

	def print_square(self):
		for i, num in enumerate(self.get_square(), 1):
			print(num, end=' ')
			if i % self.outer_square_size == 0:
				print()
		print()

	def solve(self):
		self.square = self.init_square(self.square)
		return self._solve()

class SudokuRulebased(Sudoku):

	def init_square(self, sudoku):
		square = []
		for i in sudoku:
			if i != self.sym_free:
				square.append({i})
			else:
				square.append(self.sym_set.copy())
		return square

	def get_square(self):
		for num in self.square:
			if len(num) == 1:
				yield setget(num)
			else:
				yield num

	def get_row_nums(self, i):
		row_set = set()
		for x in row_indices(i, self.outer_square_size):
			if len(self.square[x]) == 1 and x != i:
				row_set.update(self.square[x])
		return row_set

	def get_column_nums(self, i):
		column_set = set()
		for x in col_indices(i, self.outer_square_size):
			if len(self.square[x]) == 1 and x != i:
				column_set.update(self.square[x])
		return column_set

	def get_inner_square_nums(self, n):
		inner_square_set = set()
		for k in subblock_indices(n, self.outer_square_size, self.inner_square_size):
			if len(self.square[k]) == 1 and k != n:
				inner_square_set.update(self.square[k])
		return inner_square_set

	def update_cell(self, i):
		a = self.get_row_nums(i)
		b = self.get_column_nums(i)
		c = self.get_inner_square_nums(i)
		self.square[i] -= a
		self.square[i] -= b
		self.square[i] -= c

	def _solve(self):
		while not self.solved:
			self.solved = True
			square_old = deepcopy(self.square)
			for i in range(self.outer_square_area):
				if len(self.square[i]) != 1:
					self.solved = False
					#print_confirm("#%u is unsolved -> solve" % i)
					self.update_cell(i)
					#print_confirm(self.square)
			if square_old == self.square and not self.solved:
				raise NotImplementedError("Sudoku not solvable using this method")
		return self.square

class SudokuBruteforce(Sudoku):

	def init_square(self, sudoku):
		return sudoku

	def get_square(self):
		return self.square

	def get_row_nums(self, i):
		row_set = set()
		for x in row_indices(i, self.outer_square_size):
			if x != i:
				row_set.add(self.square[x])
		return row_set

	def get_column_nums(self, i):
		column_set = set()
		for x in col_indices(i, self.outer_square_size):
			if x != i:
				column_set.add(self.square[x])
		return column_set

	def get_inner_square_nums(self, i):
		inner_square_set = set()
		for x in subblock_indices(i, self.outer_square_size, self.inner_square_size):
			if x != i:
				inner_square_set.add(self.square[x])
		return inner_square_set

	def get_possible_nums(self, i):
		all = self.get_row_nums(i) | self.get_column_nums(i) | self.get_inner_square_nums(i)
		return self.sym_set - all

	def get_next_higher_possible_num(self, i, num):
		for pn in sorted(self.get_possible_nums(i)): # fixme: sorting is bad here
			if pn > num:
				return pn
		return self.sym_free

	def _solve(self):
		i = 0
		backtrack = []
		backtracks = 0
		steps = 0

		while i < self.outer_square_area:
			if self.square[i] != self.sym_free:
				i+=1
				continue
			pnums = self.get_possible_nums(i)
			#print(pnums)
			#self.print_square()

			if len(pnums) == 0:
				while True:
					backtracks += 1
					try:
						j, num = backtrack.pop()
					except IndexError:
						raise Unsolvable

					num = self.get_next_higher_possible_num(j, num)
					self.square[j] = num
					if num != self.sym_free:
						backtrack.append((j, num))
						i = j+1
						break
			else:
				num = min(pnums)
				self.square[i] = num
				backtrack.append((i, num))
				steps += 1

		return backtracks, steps

if __name__ == "__main__":
	from future.utils import viewitems
	from genutility.time import MeasureTime

	for name, sud in viewitems(sudokus):
		s = SudokuBruteforce(9, sud, set(range(1, 10)), 0)
		try:
			with MeasureTime() as t:
				steps, backtracks = s.solve()
		except Unsolvable:
			print("Cannot solve Sudoku")
		else:
			s.print_square()
		print("%s: Schritte: %u, Backtracks: %u, time: %f" % (name, steps, backtracks, t.get()))
