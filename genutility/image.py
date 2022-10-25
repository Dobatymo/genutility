from __future__ import generator_stop

from fractions import Fraction
from typing import Tuple, Union

import numpy as np

from .numpy import bincount_batch, center_of_mass_2d, unblock

Rational = Union[float, Fraction]


def grayscale(arr: np.ndarray) -> np.ndarray:
    """Converts RGB/BGR images `arr` [batch..., x, y, channel] to grayscale."""

    return np.sum(arr, axis=-1) // arr.shape[-1]


def histogram_1d(arr: np.ndarray, levels: int) -> np.ndarray:

    """Input shape of `arr`: [batch..., x]. Histogrammed over x and batched over the remaining dimensions.
    Output shape: [batch..., levels]
    """

    return bincount_batch(arr, -1, levels)


def resize_oar(max_width: int, max_height: int, dar: Rational) -> Tuple[int, int]:

    maxdar = max_width / max_height

    if dar >= maxdar:  # wider than it should be
        width = max_width
        height = int(width / dar)
    else:  # thinner than it should be
        height = max_height
        width = int(height * dar)

    return width, height


def resize_maxsize(max_width: int, max_height: int, width: int, height: int) -> Tuple[int, int]:

    return resize_oar(max_width, max_height, width / height)


def histogram_2d(arr: np.ndarray, levels: int) -> np.ndarray:

    """Input shape of `arr`: [batch..., y, x]. Histogrammed over x and y and batched over
    the remaining dimensions.
    Output shape: [batch..., levels]
    """

    if len(arr.shape) < 2:
        raise ValueError("arr must be at least 2-dimensional")

    newshape = arr.shape[:-2] + (arr.shape[-2] * arr.shape[-1],)
    flattened = np.reshape(arr, newshape)

    return bincount_batch(flattened, -1, levels)


def block_histogram_2d(arr: np.ndarray, by: int, bx: int, levels: int) -> np.ndarray:

    """Input shape of `arr`: [batch..., y, x]. Histogrammed over blocks of size bx and by
    and batched over the remaining dimensions.
    Output shape: [batch..., y/by, x/bx, levels]
    """

    invx = arr.shape[-1] // bx  # dimensions in unblock go from innerst to outerst
    invy = arr.shape[-2] // by
    blocks = unblock(arr, invx, invy)
    block_hists = histogram_1d(blocks, levels)
    return block_hists.reshape(arr.shape[:-2] + (invy, invx, -1))


def image_histogram(arr: np.ndarray, levels: int = 256) -> np.ndarray:

    """Input shape of RGB/BGR image `arr`: [batch..., x, y, channel]. It is summed over channels to create a grayscale
    image, then histogrammed over x and y and batched over the remaining dimensions.
    Output shape: [batch..., levels]
    """

    if len(arr.shape) < 3:
        raise ValueError("arr must be at least 3-dimensional")

    gray = grayscale(arr)
    return histogram_2d(gray, levels)


def image_block_histogram(arr: np.ndarray, bx: int, by: int, levels: int = 256) -> np.ndarray:

    """Input shape of RGB/BGR image `arr`: [batch..., x, y, channel]. It is summed over channels to create a grayscale
    image, then histogrammed over x and y and batched over the remaining dimensions.
    Output shape: [batch..., bx, by, levels]
    """

    if len(arr.shape) < 3:
        raise ValueError("arr must be at least 3-dimensional")

    gray = grayscale(arr)
    return block_histogram_2d(gray, bx, by, levels)


def center_of_mass_quadrant(img: np.ndarray) -> int:
    """Returns the image quadrant of the center of mass of the grayscale image `img`:
    +---+---+
    | 0 | 1 |
    +---+---+
    | 3 | 2 |
    +---+---+
    """

    if len(img.shape) != 2:
        raise ValueError("Grayscale image expected")

    cm_y, cm_x = center_of_mass_2d(img)
    d_y, d_x = img.shape
    c_y = (d_y - 1) / 2
    c_x = (d_x - 1) / 2

    if cm_y < c_y:
        if cm_x < c_x:
            quadrant = 0
        else:
            quadrant = 1
    else:
        if cm_x < c_x:
            quadrant = 3
        else:
            quadrant = 2

    return quadrant


def normalize_image_rotation(img: np.ndarray, img_gray: np.ndarray) -> np.ndarray:
    quadrant = center_of_mass_quadrant(img_gray)
    return np.rot90(img, k=quadrant, axes=(0, 1))
