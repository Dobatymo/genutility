from __future__ import absolute_import, division, print_function, unicode_literals

from typing import TYPE_CHECKING

import numpy as np

from .numpy import bincount_batch, unblock

if TYPE_CHECKING:
	from fractions import Fraction
	from typing import Tuple, Union
	Rational = Union[float, Fraction]

def grayscale(arr):
	return np.sum(arr, axis=-1) // arr.shape[-1]

def histogram_1d(arr, levels):
	# type: (np.ndarray, int) -> np.ndarray

	""" Input shape of `arr`: [batch..., x]. Histogrammed over x and batched over the remaining dimensions.
		Output shape: [batch..., levels]
	"""

	return bincount_batch(arr, -1, levels)

def resize_oar(max_width, max_height, dar):
	# type: (int, int, Rational) -> Tuple[int, int]

	maxdar = max_width / max_height

	if dar >= maxdar:  # wider than it should be
		width = max_width
		height = int(width / dar)
	else:  # thinner than it should be
		height = max_height
		width = int(height * dar)

	return width, height

def resize_maxsize(max_width, max_height, width, height):
	# type: (int, int, int, int) -> Tuple[int, int]

	return resize_oar(max_width, max_height, width / height)

def histogram_2d(arr, levels):
	# type: (np.ndarray, int) -> np.ndarray

	""" Input shape of `arr`: [batch..., y, x]. Histogrammed over x and y and batched over
		the remaining dimensions.
		Output shape: [batch..., levels]
	"""

	if len(arr.shape) < 2:
		raise ValueError("arr must be at least 2-dimensional")

	newshape = arr.shape[:-2] + (arr.shape[-2] * arr.shape[-1], )
	flattened = np.reshape(arr, newshape)

	return bincount_batch(flattened, -1, levels)

def block_histogram_2d(arr, by, bx, levels):
	# type: (np.ndarray, int, int, int) -> np.ndarray

	""" Input shape of `arr`: [batch..., y, x]. Histogrammed over blocks of size bx and by
		and batched over the remaining dimensions.
		Output shape: [batch..., y/by, x/bx, levels]
	"""

	invx = arr.shape[-1] // bx  # dimensions in unblock go from innerst to outerst
	invy = arr.shape[-2] // by
	blocks = unblock(arr, invx, invy)
	block_hists = histogram_1d(blocks, levels)
	return block_hists.reshape(arr.shape[:-2] + (invy, invx, -1))

def image_histogram(arr, levels=256):
	# type: (np.ndarray, int) -> np.ndarray

	""" Input shape of `arr`: [batch..., x, y, channel]. It is summed over channels to create a grayscale
		image, then histogrammed over x and y and batched over the remaining dimensions.
		Output shape: [batch..., levels]
	"""

	if len(arr.shape) < 3:
		raise ValueError("arr must be at least 3-dimensional")

	gray = grayscale(arr)
	return histogram_2d(gray, levels)

def image_block_histogram(arr, bx, by, levels=256):
	# type: (np.ndarray, int, int, int) -> np.ndarray

	""" Input shape of `arr`: [batch..., x, y, channels]. It is summed over channels to create a grayscale
		image, then histogrammed over x and y and batched over the remaining dimensions.
		Output shape: [batch..., bx, by, levels]
	"""

	if len(arr.shape) < 3:
		raise ValueError("arr must be at least 3-dimensional")

	gray = grayscale(arr)
	return block_histogram_2d(gray, bx, by, levels)
