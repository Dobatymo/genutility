import numpy as np
from PIL import Image, ImageOps

from genutility.image import (
    block_histogram_2d,
    center_of_mass_quadrant,
    grayscale,
    histogram_1d,
    histogram_2d,
    normalize_image_rotation,
    resize_oar,
)
from genutility.test import MyTestCase, parametrize


class ImageTest(MyTestCase):
    @parametrize(
        (100, 100, 1.0, (100, 100)),
        (100, 100, 2.0, (100, 50)),
        (100, 100, 0.5, (50, 100)),
        (100, 50, 1.0, (50, 50)),
        (100, 50, 2.0, (100, 50)),
        (100, 50, 0.5, (25, 50)),
        (50, 100, 1.0, (50, 50)),
        (50, 100, 2.0, (50, 25)),
        (50, 100, 0.5, (50, 100)),
    )
    def test_resize_oar_dar(self, max_width, max_height, dar, truth):
        result = resize_oar(max_width, max_height, dar)
        self.assertEqual(truth, result)

    @parametrize(
        ([[[1], [2]], [[3], [4]]], [[1, 2], [3, 4]]),
        ([[[1, 3], [2, 4]], [[3, 5], [4, 6]]], [[2, 3], [4, 5]]),
    )
    def test_grayscale(self, img, truth):
        img = np.array(img)
        result = grayscale(img)
        truth = np.array(truth)
        self.assertTrue(np.array_equal(truth, result))

    @parametrize(
        ([1, 2, 3, 4], 8, [0, 1, 1, 1, 1, 0, 0, 0]),  # single
        ([[1, 2], [3, 4]], 8, [[0, 1, 1, 0, 0, 0, 0, 0], [0, 0, 0, 1, 1, 0, 0, 0]]),  # batch
    )
    def test_histogram_1d(self, img, levels, truth):
        img = np.array(img)
        result = histogram_1d(img, levels)
        truth = np.array(truth)
        self.assertTrue(np.array_equal(truth, result))

    @parametrize(
        ([[1, 2], [3, 4]], 8, [0, 1, 1, 1, 1, 0, 0, 0]),
    )
    def test_histogram_2d(self, img, levels, truth):
        img = np.array(img)
        result = histogram_2d(img, levels)
        truth = np.array(truth)
        self.assertTrue(np.array_equal(truth, result))

    @parametrize(
        (
            [[1, 2], [3, 4]],
            1,
            1,
            8,
            [
                [[0, 1, 0, 0, 0, 0, 0, 0], [0, 0, 1, 0, 0, 0, 0, 0]],
                [[0, 0, 0, 1, 0, 0, 0, 0], [0, 0, 0, 0, 1, 0, 0, 0]],
            ],
        ),
        ([[1, 2], [3, 4]], 2, 2, 8, [[[0, 1, 1, 1, 1, 0, 0, 0]]]),
    )
    def test_block_histogram_2d(self, img, bx, by, levels, truth):
        img = np.array(img)
        result = block_histogram_2d(img, bx, by, levels)
        truth = np.array(truth)
        self.assertTrue(np.array_equal(truth, result))

    def test_center_of_mass_quadrant(self):
        for truth in range(4):
            path = f"testfiles/quadrant-{truth}.png"
            img = Image.open(path)
            img = ImageOps.grayscale(img)
            arr = np.asarray(img)
            result = center_of_mass_quadrant(arr)
            self.assertEqual(truth, result)

    def test_normalize_image_rotation(self):

        path = "testfiles/quadrant-0.png"
        with Image.open(path) as img:
            truth = np.asarray(img)

        for i in range(4):
            path = f"testfiles/quadrant-{i}.png"
            with self.subTest(i=i):
                with Image.open(path) as img:
                    img_gray = ImageOps.grayscale(img)
                    result = normalize_image_rotation(np.asarray(img), np.asarray(img_gray))
                np.testing.assert_array_equal(truth, result)


if __name__ == "__main__":
    import unittest

    unittest.main()
