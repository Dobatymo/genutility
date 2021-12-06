from __future__ import generator_stop

from functools import partial
from unittest import SkipTest

import numpy as np

from genutility.fingerprinting import hu_moments, phash_blockmean_array
from genutility.test import MyTestCase, parametrize, random_arguments


class FingerprintingTest(MyTestCase):
    @random_arguments(100, partial(np.random.uniform, size=(4, 4)))
    def test_moments(self, arr):

        try:
            import cv2
        except ImportError:
            raise SkipTest("Missing imports. pip install opencv-python")

        truth = cv2.HuMoments(cv2.moments(arr))
        result = hu_moments(np.expand_dims(arr, axis=-1))

        try:
            np.testing.assert_almost_equal(truth, result)
        except AssertionError:
            print(arr)
            inx = np.arange(7)
            bools = np.isclose(truth, result).flatten()
            print("Failed indices", inx[~bools])
            raise

    @parametrize(
        (np.zeros((4, 4)), 16, np.array([255, 255])),
        (np.eye(4), 4, np.array([144])),
    )
    def test_blockmean(self, arr, bits, truth):
        result = phash_blockmean_array(arr, bits)
        np.testing.assert_equal(truth, result)


if __name__ == "__main__":
    import unittest

    unittest.main()
