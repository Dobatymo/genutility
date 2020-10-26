from __future__ import absolute_import, division, print_function, unicode_literals

from builtins import range
from future.utils import viewitems

from math import exp, sqrt
from typing import TYPE_CHECKING

import numpy as np

from .numba import opjit

if TYPE_CHECKING:
	from typing import Callable, Iterator, Tuple, TypeVar
	T = TypeVar("T")

RGB_YELLOW = (255, 255, 0)
RGB_WHITE = (255, 255, 255)

def assert_square(name, value):
	# type: (str, np.ndarray) -> None

	""" Raises a ValueError if matrix `value` is not square.
		value: [A, A]
	"""

	if not len(value.shape) == 2 or value.shape[0] != value.shape[1]:
		raise ValueError("{} must be a square".format(name))

def normalized_choice(p_ind, p_prob):  # is this neccessary? I think `np.random.choice` can handle unnormalized probabilities
	return np.random.choice(p_ind, p=p_prob/np.sum(p_prob))

def shannon_entropy(ps, base=2):
	# type: (np.ndarray, int) -> float

	""" Calculates the Shannon entropy for probabilities `ps` with `base`. """

	return -np.sum(ps * np.log(ps) / np.log(base))

def is_rgb(img):
	# type: (np.ndarray, ) -> bool

	return len(img.shape) >= 1 and img.shape[-1] == 3

#@opjit() np.errstate doesn't work in numba...
def rgb_to_hsi(image):
	# type: (np.ndarray, ) -> np.ndarray

	""" Converts an array [..., channels] of RGB values to HSI color values (H in rad).
		RGB values are assumed to be normalized to (0, 1).
	"""

	if not is_rgb(image):
		raise ValueError("Input needs to be an array of RGB values")

	r = image[...,0]
	g = image[...,1]
	b = image[...,2]

	out = np.zeros_like(image)

	#allequal = (img == img[:, :, 0, np.newaxis]).all(axis=-1)

	with np.errstate(invalid="ignore"):
		tmp = (2.*r - g - b) / 2. / np.sqrt((r-g)**2 + (r-b)*(g-b)) # if r==g==b then 0/0

		theta = np.arccos(np.clip(tmp, -1., +1.))

		out[...,0] = np.where(b <= g, theta, 2*np.pi - theta) # H
		out[...,2] = np.sum(image, axis=-1) / 3. # I
		out[...,1] = 1 - np.amin(image, axis=-1) / out[...,2] # S if r==g==b==0 then 0/0

	np.nan_to_num(out[...,0:2], copy=False)

	return out

#@opjit() np.dot with more than 2 dimensions is not supported...
def rgb_to_ycbcr(image):
	# type: (np.ndarray, ) -> np.ndarray

	""" Converts an array [..., channels] of RGB values to Digital Y'CbCr (0-255).
		RGB values are assumed to be normalized to (0, 1).
		Don't forget to cast to uint8 for pillow.
	"""


	"""  from RGB (0-1).
	"""

	if not is_rgb(image):
		raise ValueError("Input needs to be an array of RGB values")

	m = np.array([
		[+065.481, +128.553, +024.966],
		[-037.797, -074.203, +112.000],
		[+112.000, -093.786, -018.214],
	])
	a = np.array([16, 128, 128])

	return np.dot(image, m.T) + a

def random_triangular_matrix(size, lower=True):
	# type: (int, bool) -> np.ndarray

	""" Returns a triangular matrix with random value between 0 and 1 uniformly.
	"""

	a = np.random.uniform(0, 1, (size, size))
	if lower:
		ind = np.triu_indices(5, 1)
	else:
		ind = np.tril_indices(5, 1)
	a[ind] = 0

	return a

def is_square(A):
	# type: (np.ndarray, ) -> bool

	if len(A.shape) != 2:
		return False

	if A.shape[0] != A.shape[1]:
		return False

	return True

def batch_vTAv(A, v):
	# type: (np.ndarray, np.ndarray) -> np.ndarray

	""" Performs batched calculation of `v^T A v` transform.
		Special case of bilinear form `x^T A y`

		A: float[B, X, X]
		v: float[B, X]

		returns: float[B]
	"""

	""" Faster than
		Av = np.matmul(A, v[...,:,None]) # [B, X, 1]
		return np.matmul(v[...,None,:], Av).squeeze((-2, -1)) # [B]
	"""

	return np.einsum("...k,...kl,...l->...", v, A, v)

def batch_inner(a, b, verify=True):
	# type: (np.ndarray, np.ndarray, bool) -> np.ndarray

	""" Performs a batched inner product over the last dimension.
		Replacement for deprecated `from numpy.core.umath_tests import inner1d`.
		Shapes: (B, X), (B, X) -> (B, )
	"""

	if verify and a.shape != b.shape:
		raise ValueError("All dimensions have to be equal")

	if a.shape[-1] == 0:
		return np.empty_like(a)

	return np.einsum("...i,...i->...", a, b) # faster than np.sum(a * b, axis=-1)

def batch_outer(a, b, verify=True):
	# type: (np.ndarray, np.ndarry, bool) -> np.ndarray

	""" Performs a batched outer product over the last dimension.
		Shapes: (B, X), (B, Y) -> (B, X, Y)
	"""

	if verify and a.shape[:-1] != b.shape[:-1]:
		raise ValueError("All except the last dimension have to be equal")

	return np.einsum("...i,...j->...ij", a, b) # slightly faster than np.multiply(a[...,:,None], b[...,None,:])

def batchtopk(probs, k=None, axis=-1, reverse=False):
	# type: (np.ndarray, np.ndarray, int, bool) -> np.ndarray

	""" `probs` values ndarray
		`k` take the smallest `k` elements, if `reverse` is False
			and the largest `k` if `reverse` is True
		`axis` sorting and selection axis.
	"""

	if k is not None and k <= 0:
		raise ValueError("k must be larger than 0. Use None to chose all elements.")

	if axis != -1:
		raise ValueError("Only last axis supported atm")

	if len(probs.shape) <= 1:
		raise ValueError("probs must be at least 2-dimensional")

	if reverse:
		sign = -1
	else:
		sign = 1

	indices = np.argsort(sign * probs, axis=-1) # use argpartition?
	probs = np.take_along_axis(probs, indices[...,:k], axis=-1)

	return indices, probs

#@opjit()
def logtrace(m):
	""" Calcuates the sum of the logs of the diagonal elements (batchwise if necessary)
		m: [..., x, x]
	"""

	""" note: performance cannot easily be improve by numba.
		`np.diagonal` not supported by numba 0.50.0
	"""

	return np.sum(np.log(np.diagonal(m, axis1=-2, axis2=-1)), axis=-1)

def shiftedexp(pvals):
	# type: (np.ndarray, ) -> np.ndarray

	""" Shifts `pvals` by the largest value in the last dimension
		before the exp is calculated to prevent overflow (batchwise if necessary).
		Can be used if probabilities are normalized again later.
	"""

	if pvals.shape[-1] == 0:
		return np.empty_like(pvals)

	return np.exp(pvals - np.amax(pvals, axis=-1)[...,None])

class Sampler(object):

	""" Sample from discrete CDF. """

	def __init__(self, cdf):
		self.cdf = cdf
		self.psum = cdf[-1]

	def __call__(self):
		# type: (int, ) -> int

		""" Sample one. """

		rand = np.random.uniform(0, self.psum)
		return np.searchsorted(self.cdf, rand, side="right")

	def sample(self, n):
		# type: (int, ) -> np.ndarray

		""" Sample `n`. """

		rands = np.random.uniform(0, self.psum, n)
		return np.searchsorted(self.cdf, rands, side="right")

	def pdf(self, n, minlength=None):
		out = np.bincount(self.sample(n), minlength=minlength)
		return out / n

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

	""" Sample from the categorical distribution using `pvals`.
		See: https://en.wikipedia.org/wiki/Categorical_distribution
	"""

	return sample_probabilities(pvals)() # faster than: np.argmax(np.random.multinomial(1, normalize(pvals)))

def population2cdf(population):
	# type: (np.ndarray, ) -> np.ndarray

	""" Convert a population (list of observations) to a CDF. """

	population = np.sort(population)
	return np.searchsorted(population, population, side='right') / len(population)

def pmf2cdf(pdf):
	# type: (np.ndarray, ) -> np.ndarray

	""" Convert a discrete PDF into a discrete CDF. """

	cdf = np.cumsum(pdf)
	return cdf / cdf[-1]

def _two_sample_kolmogorov_smirnov_same_length(cdf1, cdf2, n1, n2):
	# type: (np.ndarray, np.ndarray, int, int) -> Tuple[float, float]

	# note: yields different results as `scipy.stats.ks_2samp`

	if len(cdf1) != len(cdf2):
		raise ValueError("Both CDFs must have the same length")

	D = np.amax(np.abs(cdf1 - cdf2)) # K-S statistic
	level = exp(-2 * (D / sqrt((n1 + n2) / (n1 * n2)))**2)
	return D, level

def _two_sample_kolmogorov_smirnov_population(p1, p2, alpha=0.05):
	# type: (np.ndarray, np.ndarray, float) -> Tuple[float, float, bool]

	# note: yields different results as `scipy.stats.ks_2samp`

	cdf1 = population2cdf(p1)
	cdf2 = population2cdf(p2)

	statistic, pvalue = _two_sample_kolmogorov_smirnov_same_length(cdf1, cdf2, len(cdf1), len(cdf2))
	reject = pvalue < alpha
	return statistic, pvalue, reject

def _two_sample_kolmogorov_smirnov_pmf(pmf1, pmf2, alpha=0.05):
	# note: yields different results as `scipy.stats.ks_2samp`
	""" Tests the null hypothesis that both samples belong to the same distribution.
		See: https://en.wikipedia.org/wiki/Kolmogorov%E2%80%93Smirnov_test#Two-sample_Kolmogorov%E2%80%93Smirnov_test
	"""

	cdf1 = np.cumsum(pmf1)
	cdf2 = np.cumsum(pmf2)

	n1 = cdf1[-1]
	n2 = cdf2[-1]

	# cannot be inplace because of type conversion
	cdf1 = cdf1 / n1
	cdf2 = cdf2 / n2

	statistic, pvalue = _two_sample_kolmogorov_smirnov_same_length(cdf1, cdf2, n1, n2)
	reject = pvalue < alpha
	return statistic, pvalue, reject

def inf_matrix_power(pm):
	# type: (np.ndarray, ) -> np.ndarray

	""" Calculate stochastic matrix `pm` to the power of infinity,
		by finding the eigenvector which corresponds to the eigenvalue 1.
	"""

	w, v = np.linalg.eig(pm) # scipy.linalg.eig would probably by faster as it can return the left and right eigen vectors

	if not np.isclose(w[0], 1.):
		raise ValueError("The first eigenvalue is not none. Is this a right stochastic matrix?")

	vi = np.linalg.inv(v)
	d = np.zeros(pm.shape[0], dtype=np.float)
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
	if s[axis1] % n1 != 0 or s[axis2] % n2 != 0:
		raise ValueError("{}x{} does not divide by {}x{}".format(s[axis1], s[axis2], n1, n2))

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

#@opjit(cache=False) doesn't help a lot, because it's a generator
def sliding_window_2d(image, window_size, step_size=(1, 1)):
	# type: (np.ndarray, Tuple[int, int], Tuple[int, int]) -> Iterator[np.ndarray]

	win_x, win_y = window_size
	step_x, step_y = step_size
	height, width = image.shape[0:2]

	for y in range(0, height - win_y + 1, step_y):
		for x in range(0, width - win_x + 1, step_x):
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

def bincount_batch(x, axis=-1, minlength=0):
	# type: (np.ndarray, int, int) -> np.ndarray

	if x.shape[axis] == 0:
		raise ValueError("Specified axis of x cannot be 0")

	minlength = max(minlength, x.max() + 1)
	return np.apply_along_axis(np.bincount, axis, x, minlength=minlength)
