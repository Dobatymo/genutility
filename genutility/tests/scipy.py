import numpy as np

from genutility.scipy import linear_sum_assignment_cost
from genutility.test import MyTestCase, parametrize


class ScipyTest(MyTestCase):
    @parametrize(
        (np.eye(3), 0.0),
        (np.zeros((3, 3)), 0.0),
        (np.ones((3, 3)), 3.0),
        (np.zeros((1, 1)), 0.0),
        (np.ones((1, 1)), 1.0),
    )
    def test_linear_sum_assignment_cost(self, arr, truth):
        result = linear_sum_assignment_cost(arr)
        self.assertEqual(truth, result)


if __name__ == "__main__":
    import unittest

    unittest.main()
