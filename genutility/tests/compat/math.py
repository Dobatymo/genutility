from genutility.compat.math import prod
from genutility.test import MyTestCase, parametrize


class MathTest(MyTestCase):
    @parametrize(([], 1), ([1], 1), ([1, 2, 3], 6), (range(3), 0), (range(1, 3), 2))
    def test_prod(self, input, truth):
        result = prod(input)
        self.assertEqual(truth, result)


if __name__ == "__main__":
    import unittest

    unittest.main()
