import sys
from unittest import skipIf

from genutility.test import MyTestCase


@skipIf(sys.version_info < (3, 9), "requires Python 3.9+")
class LDATest(MyTestCase):
    def test_term_weight_one(self):
        from genutility.lda import LDATermWeight

        lda = LDATermWeight(2, tws="ONE")
        lda.M = 2
        lda.V = 3

        self.assertEqual((2, 3), lda._one(None).shape)


if __name__ == "__main__":
    import unittest

    unittest.main()
