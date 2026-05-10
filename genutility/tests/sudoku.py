import json

try:
    from importlib.resources import files
except ImportError:
    from importlib_resources import files

from genutility.sudoku import SudokuBruteforce, is_valid_solution
from genutility.test import MyTestCase


class SudokuTest(MyTestCase):
    def test_is_valid_solution_true(self):
        sym_set = {1, 2, 3, 4}

        board = [1, 2, 3, 4, 3, 4, 1, 2, 2, 3, 4, 1, 4, 1, 2, 3]
        result = is_valid_solution(board, sym_set)
        self.assertTrue(result)

        board = [2, 1, 3, 4, 3, 4, 1, 2, 1, 2, 4, 3, 4, 3, 2, 1]
        result = is_valid_solution(board, sym_set)
        self.assertTrue(result)

    def test_is_valid_solution_false(self):
        sym_set = {1, 2, 3, 4}

        board = [1, 2, 3, 4, 1, 2, 3, 4, 1, 2, 3, 4, 1, 2, 3, 4]
        result = is_valid_solution(board, sym_set)
        self.assertFalse(result)

        board = [1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4]
        result = is_valid_solution(board, sym_set)
        self.assertFalse(result)

    def test_sudoku_bruteforce(self):
        sudokus = json.loads(files("genutility").joinpath("data", "sudokus.json").read_text(encoding="utf-8"))
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
