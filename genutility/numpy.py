from __future__ import absolute_import, division, print_function, unicode_literals

from builtins import range
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
	from typing import Iterator, Tuple

RGB_YELLOW = (255, 255, 0)
RGB_WHITE = (255, 255, 255)

def decompress(selectors, data, default):
	# type: (np.ndarray[bool], np.ndarray[T], T) -> None

	""" Same result as:
		`np.array(list(genutility.iter.decompress(selectors, iter(data), default)))`
		but faster
	"""

	out = np.full(len(selectors), default)
	out[selectors] = data
	return out

def unblock(arr, n1, n2, axis1=-1, axis2=-2, blocksize=False):

	""" Inverse of np.block.
		Set axis to (-2, -1) to modify the order of the result.
	"""

	""" test (stackoverflow): Ok, so considering I have N block matrices with bm x bn dimension and want to stack them in a m x n matrix, provided N = m x n, I would then have x.reshape(m,n,bm,bn).swapaxes(1,2).reshape(bm*m,-1)
	"""

	s = np.array(arr.shape)
	assert s[axis1] % n1 == 0 and s[axis2] % n2 == 0, "{}x{} does not divide by {}x{}".format(s[axis1], s[axis2], n1, n2)

	if blocksize:
		n1 = s[axis1] // n1
		n2 = s[axis2] // n2

	arr = np.array(np.split(arr, n1, axis1))
	arr = np.array(np.split(arr, n2, axis2))

	inv_blocksize = n1 * n2
	total = s[axis1] * s[axis2]
	s[axis2] = inv_blocksize
	s[axis1] = total // inv_blocksize

	return np.reshape(arr, s)

def remove_color(img, ratio, neutral_color=RGB_WHITE):
	# type: (np.ndarray, float, Tuple[int, int, int]) -> np.ndarray

	""" Replace colored pixels with a `neutral_color`. The `ratio` defines the 'colorfulness' above
		which level the pixel should be replace.
		I.e. if the `ratio` is 1 nothing will be replaced,
		if `ratio` is 0 only strict greys are kept unmodified.
	"""

	channels = img.shape[-1]
	assert channels == 3, "Not a 3 channel color image"

	norm = np.std(np.array(RGB_YELLOW)) # this is the same for all pure colors

	sd = np.std(img, axis=-1)
	img[sd > ratio*norm] = neutral_color

def sliding_window_2d(image, window_size, step_size):
	# type: (np.ndarray, Tuple[int, int], Tuple[int, int]) -> Iterator[np.ndarray]

	win_x, win_y = window_size
	step_x, step_y = step_size
	height, width = image.shape[0:2]

	for y in range(0, height - win_y, step_y):
		for x in range(0, width - win_x, step_x):
			yield image[y:y + win_y, x:x + win_x, ...]

def histogram_correlation(hist1, hist2):
	# type: (np.ndarray, np.ndarray) -> np.ndarray

	""" Input shape of `hist1` and `hist2`: [batch..., levels]. The correlation is calculated over `levels`
		and then batched over the remaining dimensions.
	"""

	assert len(hist1.shape) >= 1 and hist1.shape == hist2.shape

	h1norm = (hist1.T - np.mean(hist1, axis=-1)).T
	h2norm = (hist2.T - np.mean(hist2, axis=-1)).T

	num = np.sum(h1norm * h2norm, axis=-1)
	denom = np.sqrt(np.sum(h1norm**2, axis=-1)*np.sum(h2norm**2, axis=-1))
	return num / denom
