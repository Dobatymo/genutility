import sys
from unittest import skipIf

from genutility.test import MyTestCase


@skipIf(sys.version_info < (3, 9), "requires Python 3.9+")
class SparseMatrixTest(MyTestCase):
    def test_variable_row_matrix(self):
        from genutility.datastructures.sparse_matrix import VariableRowMatrix

        matrix = VariableRowMatrix(0)
        matrix[0, 2] = 5

        self.assertEqual(5, matrix[0, 2])
        self.assertIn(((0, 2), 5), matrix.items())
        self.assertEqual([(0, 0), (0, 1), (0, 2)], list(matrix))

        del matrix[0, 2]
        self.assertEqual(0, matrix[0, 2])


if __name__ == "__main__":
    import unittest

    unittest.main()
