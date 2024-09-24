from itertools import product
from random import shuffle

from genutility.rand import randomized
from genutility.sort import (
    OptionalValue,
    bubble_sort,
    external_sort,
    selection_sort_max,
    selection_sort_min,
    sorted_by_list,
    sorted_index,
    sorted_with_keys,
)
from genutility.test import MyTestCase, parametrize


class SortTest(MyTestCase):
    def _get_random_list(self):
        lst = list(range(20))
        shuffle(lst)
        return lst

    def test_bubble_sort(self):
        result = self._get_random_list()
        truth = sorted(result)
        bubble_sort(result)
        self.assertEqual(truth, result)

    def test_selection_sort_min(self):
        result = self._get_random_list()
        truth = sorted(result)
        selection_sort_min(result)
        self.assertEqual(truth, result)

    def test_selection_sort_max(self):
        result = self._get_random_list()
        truth = sorted(result)
        selection_sort_max(result)
        self.assertEqual(truth, result)

    @parametrize(
        ([1, 2, 3], False, [(1, 1), (2, 2), (3, 3)]),
        ([3, 2, 1], False, [(3, 3), (2, 2), (1, 1)]),
        ([1, 2, 3], True, [(1, 3), (2, 2), (3, 1)]),
        ([3, 2, 1], True, [(3, 1), (2, 2), (1, 3)]),
    )
    def test_sorted_index(self, input, reverse, truth):
        result = sorted_index(input, reverse)
        self.assertIterEqual(truth, result)

    @parametrize(
        ([1, 2, 3], [1, 2, 3], False, [1, 2, 3]),
        ([1, 2, 3], [3, 2, 1], False, [3, 2, 1]),
        ([3, 2, 1], [1, 2, 3], False, [3, 2, 1]),
        ([3, 2, 1], [3, 2, 1], False, [1, 2, 3]),
        ([1, 2, 3], [1, 2, 3], True, [3, 2, 1]),
        ([1, 2, 3], [3, 2, 1], True, [1, 2, 3]),
        ([3, 2, 1], [1, 2, 3], True, [1, 2, 3]),
        ([3, 2, 1], [3, 2, 1], True, [3, 2, 1]),
    )
    def test_sorted_by_list(self, tosort, sortby, reverse, truth):
        result = sorted_by_list(tosort, sortby, reverse)
        self.assertIterEqual(truth, result)

    @parametrize(([1, 2, 3], lambda x: -x, [(3, -3), (2, -2), (1, -1)]))
    def test_sorted_with_keys(self, input, key, truth):
        result = sorted_with_keys([1, 2, 3], key)
        self.assertIterEqual(truth, result)

    def test_external_sort(self):
        seq = list(map(str, range(10)))

        for _i, max_lines in product(range(5), range(10)):
            input = randomized(seq)
            result = external_sort(input, "testtemp/external_sort_{}.gz", "t", int, max_lines)
            self.assertIterEqual(sorted(input), result, f"Failed for {input}, {max_lines}")

    @parametrize(
        ([3, 2, 1], [1, 2, 3]),
        ([(None, 2), (None, 1)], [(None, 1), (None, 2)]),
        (["b", "a"], ["a", "b"]),
        ([(None, "b"), (None, "a")], [(None, "a"), (None, "b")]),
    )
    def test_optionalvalue(self, input, truth):
        result = sorted(input, key=OptionalValue)
        self.assertEqual(truth, result)


if __name__ == "__main__":
    import unittest

    unittest.main()
