from __future__ import absolute_import, division, print_function, unicode_literals

from builtins import range
from typing import TYPE_CHECKING

from future.utils import viewitems
from collections import defaultdict

import numpy as np

if TYPE_CHECKING:
	from typing import Iterator, Tuple

RGB_YELLOW = (255, 255, 0)
RGB_WHITE = (255, 255, 255)

def normalized_choice(p_ind, p_prob):  # is this neccessary? I think `np.random.choice` can handle unnormalized probabilities
	return np.random.choice(p_ind, p=p_prob/np.sum(p_prob))

def issquare(A):
	# type: (np.ndarray, ) -> bool

	if len(A.shape) != 2:
		return False

	if A.shape[0] != A.shape[1]:
		return False

	return True

def batchtopk(probs, k=None, axis=-1, reverse=False):
	# type: (np.ndarray, np.ndarray, int) -> np.ndarray

	""" `probs` values ndarray
		`k` take the smallest `k` elements, if `reverse` is False
			and the largest `k` if `reverse` is True
		`axis` sorting and selection axis.
	"""

	assert k is None or k > 0, "k must be larger than zero. Use None to chose all elements."
	assert axis == -1, "Only last axis supported atm"
	assert len(probs.shape) > 1

	if reverse:
		sign = -1
	else:
		sign = 1

	indices = np.argsort(sign * probs, axis=-1) # use argpartition?
	probs = np.take_along_axis(probs, indices[...,:k], axis=-1)

	return indices, probs

def logtrace(m):
	""" Calcuates the sum of the logs of the diagonal elements (batchwise if neccessary)
		m: [..., x, x]
	"""

	return np.sum(np.log(np.diagonal(m, axis1=-2, axis2=-1)), axis=-1)

def shiftedexp(pvals):
	# type: (np.ndarray, ) -> np.ndarray

	""" Prevents overflow. Can be used if probabilities are normalized again later.
	"""

	return np.exp(pvals - np.max(pvals))

class Sampler(object):

	def __init__(self, cdf):
		self.cdf = cdf
		self.psum = cdf[-1]

	def __call__(self):
		rand = np.random.uniform(0, self.psum)
		return np.searchsorted(self.cdf, rand, side="right")

def sample_probabilities(pvals):
	# type: (np.ndarray, ) -> Callable[[], int]

	""" Sample from list of probabilities `pvals` with replacement.
		The probabilities don't need to be normalized.
	"""

	return Sampler(np.cumsum(pvals))

class UnboundedSparseMatrix(object):

	def __init__(self, dtype=float):
		# type: (type, ) -> None

		self.dtype = dtype
		self.zero = self.dtype(0)
		self.m = dict()
		self.cols = 0
		self.rows = 0

	def __getitem__(self, slice):
		# type: (tuple, ) -> T

		return self.m.get(slice, self.zero)

	def __setitem__(self, slice, value):
		# type: (tuple, T) -> None

		c, r = slice
		self.cols = max(self.cols, c+1)
		self.rows = max(self.rows, r+1)
		self.m[slice] = value

	def todense(self):
		# type: () -> np.ndarray

		ret = np.zeros((self.cols, self.rows), dtype=self.dtype)

		for slice, value in viewitems(self.m):
			ret[slice] = value

		return ret

def normalize(pvals):
	# type: (np.ndarray, ) -> np.ndarray

	return pvals / np.sum(pvals)

def categorical(pvals):
	# type: (np.ndarray, ) -> int

	""" Requires normalized inputs: sum(pvals) ~= 1 """

	return np.argmax(np.random.multinomial(1, pvals))

def inf_matrix_power(pm):
	w, v = np.linalg.eig(pm) # scipy.linalg.eig would probably by faster as it can return the left and right eigen vectors

	if not np.isclose(w[0], 1.):
		raise ValueError("The first eigenvalue is not none. Is this a right stochastic matrix?")

	vi = np.linalg.inv(v)
	d = np.zeros(m.shape[0], dtype=np.float)
	d[0] = 1.

	return np.matmul(v, np.matmul(np.diag(d), vi))

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
