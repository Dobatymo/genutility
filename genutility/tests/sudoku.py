from __future__ import generator_stop

import pkg_resources

from genutility.json import read_json
from genutility.sudoku import SudokuBruteforce, is_valid_solution
from genutility.test import MyTestCase


class SudokuTest(MyTestCase):

	def test_is_valid_solution_true(self):
		sym_set = {1, 2, 3, 4}

		board = [1,2,3,4, 3,4,1,2, 2,3,4,1, 4,1,2,3]
		result = is_valid_solution(board, sym_set)
		self.assertTrue(result)

		board = [2,1,3,4, 3,4,1,2, 1,2,4,3, 4,3,2,1]
		result = is_valid_solution(board, sym_set)
		self.assertTrue(result)

	def test_is_valid_solution_false(self):
		sym_set = {1, 2, 3, 4}

		board = [1,2,3,4, 1,2,3,4, 1,2,3,4, 1,2,3,4]
		result = is_valid_solution(board, sym_set)
		self.assertFalse(result)

		board = [1,1,1,1, 2,2,2,2, 3,3,3,3, 4,4,4,4]
		result = is_valid_solution(board, sym_set)
		self.assertFalse(result)

	def test_sudoku_bruteforce(self):

		sudokus = read_json(pkg_resources.resource_filename("genutility", "data/sudokus.json"))
		sym_set = set(sudokus["symbols"])
		sym_free = sudokus["free"]

		tests = ["very_easy", "easy", "normal", "hard", "very", "suck", "arto_inkala"]

		for name in tests:
			board = sudokus["boards"][name]
			s = SudokuBruteforce(board, sym_set, sym_free)
			steps, backtracks = s.solve()
			self.assertTrue(is_valid_solution(s.square, sym_set))

if __name__ == "__main__":
	import unittest
	unittest.main()
