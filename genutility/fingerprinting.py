from __future__ import generator_stop

import logging
from typing import TYPE_CHECKING

import numpy as np
from PIL import ImageFilter

# from .numba import opjit
from .numpy import rgb_to_hsi, rgb_to_ycbcr, unblock

# fingerprinting aka perceptual hashing

if TYPE_CHECKING:
    from PIL import Image


def phash_antijpeg(image):
    # type: (Image, ) -> np.ndarray

    """Source: An Anti-JPEG Compression Image Perceptual Hashing Algorithm
    `image` is a RGB pillow image.
    """

    raise NotImplementedError


def hu_moments(channels):

    """Calculates all Hu invariant image moments for all channels separately.
    Input array must be of shape [width, height, channels]
    Returns shape [moments, channels]
    """

    # pre-calculate matrices
    n, m, _ = channels.shape
    coords_x, coords_y = np.meshgrid(np.arange(m), np.arange(n))
    coords_x = np.expand_dims(coords_x, axis=-1)  # for batch input, some change is needed here
    coords_y = np.expand_dims(coords_y, axis=-1)  # for batch input, some change is needed here

    def M(p, q):
        return np.sum(coords_x**p * coords_y**q * channels, axis=(-2, -3))

    def mu(p, q, xb, yb):
        return np.sum((coords_x - xb) ** p * (coords_y - yb) ** q * channels, axis=(-2, -3))

    def eta(p, q, xb, yb, mu00):
        gamma = (p + q) / 2 + 1
        return mu(p, q, xb, yb) / mu00**gamma

    def loop():

        M00 = M(0, 0)
        if not np.all(M00 > 0.0):
            logging.error("M00: %s", M00)
            raise ValueError("Failed to calculate moments. Single color pictures are not supported yet.")

        M10 = M(1, 0)
        M01 = M(0, 1)
        xb = M10 / M00
        yb = M01 / M00

        mu00 = mu(0, 0, xb, yb)

        eta20 = eta(2, 0, xb, yb, mu00)
        eta02 = eta(0, 2, xb, yb, mu00)
        eta11 = eta(1, 1, xb, yb, mu00)
        eta30 = eta(3, 0, xb, yb, mu00)
        eta12 = eta(1, 2, xb, yb, mu00)
        eta21 = eta(2, 1, xb, yb, mu00)
        eta03 = eta(0, 3, xb, yb, mu00)

        phi1 = eta20 + eta02
        phi2 = (eta20 - eta02) ** 2 + 4 * eta11**2
        phi3 = (eta30 - 3 * eta12) ** 2 + (3 * eta21 - eta03) ** 2
        phi4 = (eta30 + eta12) ** 2 + (eta21 + eta03) ** 2
        phi5 = (eta30 - 3 * eta12) * (eta30 + eta12) * ((eta30 + eta12) ** 2 - 3 * (eta21 + eta03) ** 2) + (
            3 * eta21 - eta03
        ) * (eta21 + eta03) * (3 * (eta30 + eta12) ** 2 - (eta21 + eta03) ** 2)
        phi6 = (eta20 - eta02) * ((eta30 + eta12) ** 2 - (eta21 + eta03) ** 2) + 4 * eta11 * (eta30 + eta12) * (
            eta21 + eta03
        )
        phi7 = (3 * eta21 - eta03) * (eta30 + eta12) * ((eta30 + eta12) ** 2 - 3 * (eta21 + eta03) ** 2) - (
            eta30 - 3 * eta12
        ) * (eta21 + eta03) * (3 * (eta30 + eta12) ** 2 - (eta21 + eta03) ** 2)

        return np.array([phi1, phi2, phi3, phi4, phi5, phi6, phi7])

    return loop()


# @opjit() rgb_to_hsi and rgb_to_ycbcr not supported by numba
def phash_moments_array(arr):
    arr = arr / 255.0

    # convert colorspaces
    hsi = rgb_to_hsi(arr)
    ycbcr = rgb_to_ycbcr(arr)  # .astype(np.uint8)
    channels = np.concatenate([hsi, ycbcr], axis=-1)
    return np.concatenate(hu_moments(channels).T)


def phash_moments(image):
    # type: (Image, ) -> np.ndarray

    """Source: Perceptual Hashing for Color Images Using Invariant Moments
    `image` is a RGB pillow image. Results should be compared with L^2-Norm of difference vector.
    """

    if image.mode != "RGB":
        raise ValueError("Only RGB images are supported")

    # preprocessing
    image = image.resize((512, 512), Image.BICUBIC)
    image = image.filter(ImageFilter.GaussianBlur(3))
    image = np.array(image)
    return phash_moments_array(image)


def phash_blockmean_array(arr, bits=256):
    # type: (np.ndarray, int) -> np.ndarray

    """If bits is not a multiple of 8,
    the result will be zero padded from the right.
    """

    if len(arr.shape) != 2:
        raise ValueError("arr must be 2-dimensional")

    n = int(np.sqrt(bits))
    if n**2 != bits:
        raise ValueError("bits must be a square number")

    blocks = unblock(arr, n, n)
    means = np.mean(blocks, axis=-1)
    median = np.median(means)
    bools = means >= median
    return np.packbits(bools)


def phash_blockmean(image, bits=256, x=256):
    # type: (Image, int, int) -> bytes

    """Source: Block Mean Value Based Image Perceptual Hashing
    Method: 1
    Metric: 'Bit error rate' (normalized hamming distance)
    """

    image = image.convert("L").resize((x, x))
    image = np.array(image)
    return phash_blockmean_array(image, bits).tobytes()
