from __future__ import generator_stop

from copy import deepcopy
from typing import Collection, Generic, Optional, Set, Tuple, TypeVar

from .compat.math import isqrt
from .exceptions import assert_type
from .indexing import col_indices, row_indices, subblock_indices
from .iter import batch
from .set import get as setget

T = TypeVar("T")


class Unsolvable(Exception):
    pass


class Sudoku(Generic[T]):
    def __init__(self, board, sym_set, sym_free):
        # type: (Collection[T], Set[T], T) -> None

        assert_type("sym_set", sym_set, set)

        self.square = board
        self.sym_set = sym_set
        self.sym_free = sym_free

        self.outer_square_size = isqrt(len(board))
        self.outer_square_area = self.outer_square_size**2
        if self.outer_square_area != len(board):
            raise ValueError("board has an invalid size")

        if self.outer_square_size != len(sym_set):
            raise ValueError(
                f"sym_set length must be equal to the edge length of the board: {len(sym_set)} vs {self.outer_square_area}"
            )

        self.inner_square_size = isqrt(self.outer_square_size)
        if self.inner_square_size**2 != self.outer_square_size:
            raise ValueError("board has an invalid size")

        self.solved = False

    def init_board(self, board):
        # type: (Collection[T], ) -> Collection[T]

        raise NotImplementedError

    def get_board(self):
        # type: () -> Collection[T]

        raise NotImplementedError

    def print_square(self):
        # type: () -> None

        for i, num in enumerate(self.get_board(), 1):
            print(num, end=" ")
            if i % self.outer_square_size == 0:
                print()

    def solve(self, strategy=None):
        # type: (Optional[str], ) -> Collection[T]

        self.square = self.init_board(self.square)
        return self._solve(strategy)

    def _solve(self, strategy=None):
        # type: (Optional[str], ) -> Collection[T]

        raise NotImplementedError


class SudokuRulebased(Sudoku):
    def init_board(self, board):
        square = []
        for i in board:
            if i != self.sym_free:
                square.append({i})
            else:
                square.append(self.sym_set.copy())
        return square

    def get_board(self):
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

    def _solve(self, strategy=None):
        while not self.solved:
            self.solved = True
            square_old = deepcopy(self.square)
            for i in range(self.outer_square_area):
                if len(self.square[i]) != 1:
                    self.solved = False
                    # print_confirm("#%u is unsolved -> solve" % i)
                    self.update_cell(i)
                    # print_confirm(self.square)
            if square_old == self.square and not self.solved:
                raise NotImplementedError("Sudoku not solvable using this method")
        return self.square


class SudokuBruteforce(Sudoku):
    def init_board(self, board):
        return board

    def get_board(self):
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
        # type: (int, ) -> Set[T]

        all = self.get_row_nums(i) | self.get_column_nums(i) | self.get_inner_square_nums(i)
        return self.sym_set - all

    def get_next_higher_possible_num(self, i, num):
        for pn in sorted(
            self.get_possible_nums(i)
        ):  # fixme: sorting is bad here. # why? for algorithmic performance or python performance?
            if pn > num:
                return pn

        return self.sym_free

    def get_next_lower_possible_num(self, i, num):
        for pn in sorted(self.get_possible_nums(i), reverse=False):  # see: get_next_higher_possible_num
            if pn < num:
                return pn

        return self.sym_free

    def _solve(self, strategy=None):

        strategy = strategy or "inc"

        try:
            candidate_func = {
                "inc": self.get_next_higher_possible_num,
                "dec": self.get_next_lower_possible_num,
            }[strategy]

            selection_func = {
                "inc": min,
                "dec": max,
            }[strategy]

        except KeyError:
            raise ValueError("Invalid strategy")

        i = 0
        backtrack = []  # type: Tuple[int, T]
        backtracks = 0
        steps = 0

        while i < self.outer_square_area:
            if self.square[i] != self.sym_free:
                i += 1
                continue
            pnums = self.get_possible_nums(i)

            if len(pnums) == 0:
                while True:
                    backtracks += 1
                    try:
                        j, num = backtrack.pop()
                    except IndexError:
                        raise Unsolvable

                    num = candidate_func(j, num)
                    self.square[j] = num
                    if num != self.sym_free:
                        backtrack.append((j, num))
                        i = j + 1
                        break
            else:
                num = selection_func(pnums)
                self.square[i] = num
                backtrack.append((i, num))
                steps += 1

        return backtracks, steps


def is_valid_solution(board, sym_set):
    # type: (Collection[T], Set[T]) -> bool

    """Checks if `board` is a valid solved Sudoku configuration"""

    edge_len = isqrt(len(board))
    square_len = isqrt(edge_len)

    board = tuple(batch(board, edge_len, func=tuple))

    # check rows
    for j in range(edge_len):
        row = {board[j][i] for i in range(edge_len)}
        if set(row) != sym_set:
            return False

    # check cols
    for i in range(edge_len):
        col = {board[j][i] for j in range(edge_len)}
        if col != sym_set:
            return False

    # check inner squares
    for x in range(0, edge_len, square_len):
        for y in range(0, edge_len, square_len):
            square = {board[i][j] for i in range(x, x + square_len) for j in range(y, y + square_len)}
            if square != sym_set:
                return False

    return True


if __name__ == "__main__":

    from argparse import ArgumentParser

    from genutility.time import MeasureTime

    parser = ArgumentParser()
    parser.add_argument("board", metavar="N", type=int, nargs="+", help="Flat Sudoku board")
    parser.add_argument("--symbols", default=set(range(1, 10)), type=int, nargs="+", help="Used symbols")
    parser.add_argument("--free", default=0, help="Free marker symbol")
    parser.add_argument("--strategy", choices=("inc", "dec"), default="linear")
    args = parser.parse_args()

    sym_set = set(args.symbols)

    s = SudokuBruteforce(args.board, sym_set, args.free)

    try:
        with MeasureTime() as t:
            steps, backtracks = s.solve(args.strategy)

        s.print_square()
        if is_valid_solution(args.board, sym_set):
            print(f"Solved sudoku in {t.get():.2} seconds, using {steps} steps and backtracked {backtracks} times.")
        else:
            print(
                f"No valid solution was found in {t.get():.2} seconds, using {steps} steps and backtracked {backtracks} times."
            )
    except Unsolvable:
        print("Sudoku is not solvable")
