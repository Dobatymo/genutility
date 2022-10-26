from __future__ import generator_stop

from math import exp, sqrt
from typing import Any, Callable, Dict, Generic, Iterator, Optional, Sequence, Tuple, TypeVar

import numpy as np

# from .numba import opjit

T = TypeVar("T")

RGB_YELLOW = (255, 255, 0)
RGB_WHITE = (255, 255, 255)


def assert_square(name: str, value: np.ndarray) -> None:

    """Raises a ValueError if matrix `value` is not square.
    value: [A, A]
    """

    if not len(value.shape) == 2 or value.shape[0] != value.shape[1]:
        raise ValueError(f"{name} must be a square")


def normalized_choice(
    p_ind, p_prob
):  # is this neccessary? I think `np.random.choice` can handle unnormalized probabilities
    return np.random.choice(p_ind, p=p_prob / np.sum(p_prob))


def shannon_entropy(ps: np.ndarray, base: int = 2) -> float:

    """Calculates the Shannon entropy for probabilities `ps` with `base`."""

    return -np.sum(ps * np.log(ps) / np.log(base))


def is_rgb(img: np.ndarray) -> bool:
    """Simply tests if `img` has 3 channels."""

    return len(img.shape) >= 1 and img.shape[-1] == 3


# @opjit() # np.errstate doesn't work in numba...
def rgb_to_hsi(image: np.ndarray) -> np.ndarray:

    """Converts an array [..., channels] of RGB values to HSI color values (H in rad).
    RGB values are assumed to be normalized to (0, 1).
    """

    if not is_rgb(image):
        raise ValueError("Input needs to be an array of RGB values")

    r = image[..., 0]
    g = image[..., 1]
    b = image[..., 2]

    out = np.zeros_like(image)

    # allequal = (img == img[:, :, 0, np.newaxis]).all(axis=-1)

    with np.errstate(invalid="ignore"):
        tmp = (2.0 * r - g - b) / 2.0 / np.sqrt((r - g) ** 2 + (r - b) * (g - b))  # if r==g==b then 0/0

        theta = np.arccos(np.clip(tmp, -1.0, +1.0))

        out[..., 0] = np.where(b <= g, theta, 2 * np.pi - theta)  # H
        out[..., 2] = np.sum(image, axis=-1) / 3.0  # I
        out[..., 1] = 1 - np.amin(image, axis=-1) / out[..., 2]  # S if r==g==b==0 then 0/0

    np.nan_to_num(out[..., 0:2], copy=False)

    return out


# @opjit() # np.dot with more than 2 dimensions is not supported...
def rgb_to_ycbcr(image: np.ndarray) -> np.ndarray:

    """Converts an array [..., channels] of RGB values to Digital Y'CbCr (0-255).
    RGB values are assumed to be normalized to (0, 1).
    Don't forget to cast to uint8 for pillow.
    """

    """  from RGB (0-1).
    """

    if not is_rgb(image):
        raise ValueError("Input needs to be an array of RGB values")

    m = np.array(
        [
            [+065.481, +128.553, +024.966],
            [-037.797, -074.203, +112.000],
            [+112.000, -093.786, -018.214],
        ]
    )
    a = np.array([16, 128, 128])

    return np.dot(image, m.T) + a


def random_triangular_matrix(size: int, lower: bool = True) -> np.ndarray:

    """Returns a triangular matrix with random value between 0 and 1 uniformly."""

    a = np.random.uniform(0, 1, (size, size))
    if lower:
        ind = np.triu_indices(5, 1)
    else:
        ind = np.tril_indices(5, 1)
    a[ind] = 0

    return a


def is_square(A: np.ndarray) -> bool:

    if len(A.shape) != 2:
        return False

    if A.shape[0] != A.shape[1]:
        return False

    return True


def batch_vTAv(A: np.ndarray, v: np.ndarray) -> np.ndarray:

    """Performs batched calculation of `v^T A v` transform.
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


def batch_inner(a: np.ndarray, b: np.ndarray, verify: bool = True) -> np.ndarray:

    """Performs a batched inner product over the last dimension.
    Replacement for deprecated `from numpy.core.umath_tests import inner1d`.
    Shapes: (B, X), (B, X) -> (B, )
    """

    if verify and a.shape != b.shape:
        raise ValueError("All dimensions have to be equal")

    if a.shape[-1] == 0:
        return np.empty_like(a)

    return np.einsum("...i,...i->...", a, b)  # faster than np.sum(a * b, axis=-1)


def batch_outer(a: np.ndarray, b: np.ndarray, verify: bool = True) -> np.ndarray:

    """Performs a batched outer product over the last dimension.
    Shapes: (B, X), (B, Y) -> (B, X, Y)
    """

    if verify and a.shape[:-1] != b.shape[:-1]:
        raise ValueError("All except the last dimension have to be equal")

    return np.einsum("...i,...j->...ij", a, b)  # slightly faster than np.multiply(a[...,:,None], b[...,None,:])


def batchtopk(
    probs: np.ndarray, k: Optional[int] = None, axis: int = -1, reverse: bool = False
) -> Tuple[np.ndarray, np.ndarray]:

    """`probs` values ndarray
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

    indices = np.argsort(sign * probs, axis=-1)  # use argpartition?
    probs = np.take_along_axis(probs, indices[..., :k], axis=-1)

    return indices, probs


# @opjit() # np.diagonal not supported by numba as of version 0.52.0
def logtrace(m: np.ndarray) -> np.ndarray:
    """Calcuates the sum of the logs of the diagonal elements (batchwise if necessary)
    m: [..., x, x]
    """

    """ note: performance cannot easily be improve by numba.
        `np.diagonal` not supported by numba 0.52.0
    """

    return np.sum(np.log(np.diagonal(m, axis1=-2, axis2=-1)), axis=-1)


def shiftedexp(pvals: np.ndarray) -> np.ndarray:

    """Shifts `pvals` by the largest value in the last dimension
    before the exp is calculated to prevent overflow (batchwise if necessary).
    Can be used if probabilities are normalized again later.
    """

    if pvals.shape[-1] == 0:
        return np.empty_like(pvals)

    return np.exp(pvals - np.amax(pvals, axis=-1)[..., None])


class Sampler:

    """Sample from discrete CDF."""

    def __init__(self, cdf: np.ndarray) -> None:
        self.cdf = cdf
        self.psum = cdf[-1]

    def __call__(self) -> int:

        """Sample one."""

        rand = np.random.uniform(0, self.psum)
        return np.searchsorted(self.cdf, rand, side="right")

    def sample(self, n: int) -> np.ndarray:

        """Sample `n`."""

        rands = np.random.uniform(0, self.psum, n)
        return np.searchsorted(self.cdf, rands, side="right")

    def pdf(self, n: int, minlength: Optional[int] = None) -> np.ndarray:

        out = np.bincount(self.sample(n), minlength=minlength)
        return out / n


def sample_probabilities(pvals: np.ndarray) -> Callable[[], int]:

    """Sample from list of probabilities `pvals` with replacement.
    The probabilities don't need to be normalized.
    """

    return Sampler(np.cumsum(pvals))


class UnboundedSparseMatrix(Generic[T]):
    def __init__(self, dtype: type = float) -> None:

        self.dtype = dtype
        self.zero = self.dtype(0)
        self.m: Dict[Tuple[int, int], T] = dict()
        self.cols = 0
        self.rows = 0

    def __getitem__(self, slice: Tuple[int, int]) -> T:

        return self.m.get(slice, self.zero)

    def __setitem__(self, slice: Tuple[int, int], value: T) -> None:

        c, r = slice
        self.cols = max(self.cols, c + 1)
        self.rows = max(self.rows, r + 1)
        self.m[slice] = value

    def todense(self) -> np.ndarray:

        ret = np.zeros((self.cols, self.rows), dtype=self.dtype)

        for slice, value in self.m.items():
            ret[slice] = value

        return ret


def normalize(pvals: np.ndarray) -> np.ndarray:

    return pvals / np.sum(pvals)


def categorical(pvals: np.ndarray) -> int:

    """Sample from the categorical distribution using `pvals`.
    See: https://en.wikipedia.org/wiki/Categorical_distribution
    """

    return sample_probabilities(pvals)()  # faster than: np.argmax(np.random.multinomial(1, normalize(pvals)))


def population2cdf(population: np.ndarray) -> np.ndarray:

    """Convert a population (list of observations) to a CDF."""

    population = np.sort(population)
    return np.searchsorted(population, population, side="right") / len(population)


def pmf2cdf(pdf: np.ndarray) -> np.ndarray:

    """Convert a discrete PDF into a discrete CDF."""

    cdf = np.cumsum(pdf)
    return cdf / cdf[-1]


def _two_sample_kolmogorov_smirnov_same_length(
    cdf1: np.ndarray, cdf2: np.ndarray, n1: int, n2: int
) -> Tuple[float, float]:

    # note: yields different results as `scipy.stats.ks_2samp`

    if len(cdf1) != len(cdf2):
        raise ValueError("Both CDFs must have the same length")

    D = np.amax(np.abs(cdf1 - cdf2))  # K-S statistic
    level = exp(-2 * (D / sqrt((n1 + n2) / (n1 * n2))) ** 2)
    return D, level


def _two_sample_kolmogorov_smirnov_population(
    p1: np.ndarray, p2: np.ndarray, alpha: float = 0.05
) -> Tuple[float, float, bool]:

    # note: yields different results as `scipy.stats.ks_2samp`

    cdf1 = population2cdf(p1)
    cdf2 = population2cdf(p2)

    statistic, pvalue = _two_sample_kolmogorov_smirnov_same_length(cdf1, cdf2, len(cdf1), len(cdf2))
    reject = pvalue < alpha
    return statistic, pvalue, reject


def _two_sample_kolmogorov_smirnov_pmf(
    pmf1: np.ndarray, pmf2: np.ndarray, alpha: float = 0.05
) -> Tuple[float, float, bool]:

    # note: yields different results as `scipy.stats.ks_2samp`
    """Tests the null hypothesis that both samples belong to the same distribution.
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


def inf_matrix_power(pm: np.ndarray, dtype=np.float64) -> np.ndarray:

    """Calculate stochastic matrix `pm` to the power of infinity,
    by finding the eigenvector which corresponds to the eigenvalue 1.
    """

    w, v = np.linalg.eig(
        pm
    )  # scipy.linalg.eig would probably by faster as it can return the left and right eigen vectors

    if not np.isclose(w[0], 1.0):
        raise ValueError("The first eigenvalue is not none. Is this a right stochastic matrix?")

    vi = np.linalg.inv(v)
    d = np.zeros(pm.shape[0], dtype=dtype)
    d[0] = 1.0

    return np.matmul(v, np.matmul(np.diag(d), vi))


def decompress(selectors: np.ndarray, data: np.ndarray, default) -> np.ndarray:

    """Same result as:
    `np.array(list(genutility.iter.decompress(selectors, iter(data), default)))`
    but faster.
    `selectors` should be a bool array.
    """

    out = np.full(len(selectors), default)
    out[selectors] = data
    return out


def unblock(arr: np.ndarray, n1: int, n2: int, axis1: int = -1, axis2: int = -2, blocksize: bool = False) -> np.ndarray:

    """Inverse of np.block.
    Set axis to (-2, -1) to modify the order of the result.
    """

    """ test (stackoverflow): Ok, so considering I have N block matrices with bm x bn dimension and want to stack them in a m x n matrix, provided N = m x n, I would then have x.reshape(m,n,bm,bn).swapaxes(1,2).reshape(bm*m,-1)
    """

    s = np.array(arr.shape)
    if s[axis1] % n1 != 0 or s[axis2] % n2 != 0:
        raise ValueError(f"{s[axis1]}x{s[axis2]} does not divide by {n1}x{n2}")

    if blocksize:
        n1 = s[axis1] // n1
        n2 = s[axis2] // n2

    # this first .split adds a new dimensions on the outside, so if a absolute index
    # is given for the second axis it must be moved one to the right
    if axis2 >= 0:
        _axis2 = axis2 + 1
    else:
        _axis2 = axis2

    arr = np.array(np.split(arr, n1, axis1))
    arr = np.array(np.split(arr, n2, _axis2))

    inv_blocksize = n1 * n2
    total = s[axis1] * s[axis2]
    s[axis2] = inv_blocksize
    s[axis1] = total // inv_blocksize

    return np.reshape(arr, s)


def unblock2d(arr: np.ndarray, n1: int, n2: int, blocksize: bool = False) -> np.ndarray:
    """
    arr: [width, height, ...]

    returns: (block_num, block_size)
    """

    s = np.array(arr.shape)
    if blocksize:
        bs1 = n1
        bs2 = n2
        bn1 = s[0] // n1
        bn2 = s[1] // n2
    else:
        bn1 = n1
        bn2 = n2
        bs1 = s[0] // n1
        bs2 = s[1] // n2

    if len(arr.shape) > 2:
        return arr.reshape(bn1, bs1, bn2, bs2, -1).swapaxes(1, 2).reshape(bn1 * bn2, bs1 * bs2, -1)
    else:
        return arr.reshape(bn1, bs1, bn2, bs2).swapaxes(1, 2).reshape(bn1 * bn2, bs1 * bs2)


def block2d(arr: np.ndarray, bn1: int, bn2: int, bs1: int, bs2: int) -> np.ndarray:
    """
    arr: (block_num, block_size)

    returns: (width, height)
    """

    s = np.array(arr.shape)
    assert s[0] == bn1 * bn2
    assert s[1] == bs1 * bs2

    return arr.reshape(bn1, bn2, bs1, bs2).swapaxes(1, 2).reshape(bn1 * bs1, bn2 * bs2)


def remove_color(img: np.ndarray, ratio: float, neutral_color: Tuple[int, int, int] = RGB_WHITE) -> None:

    """Replace colored pixels with a `neutral_color`. The `ratio` defines the 'colorfulness' above
    which level the pixel should be replace.
    I.e. if the `ratio` is 1 nothing will be replaced,
    if `ratio` is 0 only strict greys are kept unmodified.
    """

    channels = img.shape[-1]
    assert channels == 3, "Not a 3 channel color image"

    norm = np.std(np.array(RGB_YELLOW))  # this is the same for all pure colors

    sd = np.std(img, axis=-1)
    img[sd > ratio * norm] = neutral_color


# @opjit(cache=False) doesn't help a lot, because it's a generator
def sliding_window_2d(
    image: np.ndarray, window_size: Tuple[int, int], step_size: Tuple[int, int] = (1, 1)
) -> Iterator[np.ndarray]:

    win_x, win_y = window_size
    step_x, step_y = step_size
    height, width = image.shape[0:2]

    for y in range(0, height - win_y + 1, step_y):
        for x in range(0, width - win_x + 1, step_x):
            yield image[y : y + win_y, x : x + win_x, ...]


def histogram_correlation(hist1: np.ndarray, hist2: np.ndarray) -> np.ndarray:

    """Input shape of `hist1` and `hist2`: [batch..., levels]. The correlation is calculated over `levels`
    and then batched over the remaining dimensions.
    """

    assert len(hist1.shape) >= 1 and hist1.shape == hist2.shape

    h1norm = (hist1.T - np.mean(hist1, axis=-1)).T
    h2norm = (hist2.T - np.mean(hist2, axis=-1)).T

    num = np.sum(h1norm * h2norm, axis=-1)
    denom = np.sqrt(np.sum(h1norm**2, axis=-1) * np.sum(h2norm**2, axis=-1))
    return num / denom


def bincount_batch(x: np.ndarray, axis: int = -1, minlength: int = 0) -> np.ndarray:

    if x.shape[axis] == 0:
        raise ValueError("Specified axis of x cannot be 0")

    minlength = max(minlength, x.max() + 1)
    return np.apply_along_axis(np.bincount, axis, x, minlength=minlength)


def stochastic(x: np.ndarray) -> np.ndarray:

    """It normalizes the last dimension of an ndarray to sum to 1.
    It can be used to convert (batches of) vectors to stochastic vectors
    or (batches of) matrices to *right* stochastic matrices.
    Right stochastic matrices are also called transitions matrices.
    """

    n = np.linalg.norm(x, 1, axis=-1, keepdims=True)
    # n = np.sum(x, axis=-1, keepdims=True) # todo: same result (except dtype), which is faster?

    with np.errstate(invalid="raise"):  # see: `normalized`
        return x / n


def sequence_mask(lengths: np.ndarray, maxlen: Optional[int] = None, dtype: Any = None) -> np.ndarray:

    """cf. tf.sequence_mask
    lengths: [N]
    """

    if not lengths:
        return np.array([], dtype=dtype or np.bool_)

    if maxlen is None:
        maxlen = max(lengths)
    row_vector = np.arange(maxlen)
    matrix = np.expand_dims(lengths, -1)

    ret = row_vector < matrix
    if dtype is not None:
        ret = ret.astype(dtype)

    return ret


# @opjit() # doesn't work atm because numba doesn't support `None` indexing
def _viterbi_dense_masked(
    p_emit: np.ndarray, p_trans: np.ndarray, p_trans0: np.ndarray, mask: np.ndarray
) -> np.ndarray:

    batch_size, T, N = p_emit.shape

    N1, N2 = p_trans.shape
    assert N == N1 == N2

    assert (batch_size, T) == mask.shape
    assert (N,) == p_trans0.shape

    trellis = np.zeros((T, batch_size, N), dtype=p_emit.dtype)
    states = np.zeros((T, batch_size, N), dtype=np.intp)

    # even if sequences of length 0 should be allowed, this does not have to be masked, as there cannot be a wrong result
    trellis[0] = p_trans0 + p_emit[:, 0, :]  # broadcast p_trans0: [N] -> batch_size*[[N]]

    for t in range(1, T):
        masked_p_trans = (
            mask[:, t, None, None] * p_trans[None, :, :]
        )  # [batch_size, 1, 1] * [1, N, N] == [batch_size, N, N]
        weighted_scores = (
            trellis[t - 1, :, :, None] + masked_p_trans
        )  # [batch_size, N, N] # scores and p_trans broadcasted
        max_scores = np.amax(weighted_scores, axis=1)  # [batch_size, N]
        trellis[t] = max_scores + p_emit[:, t, :]  # [batch_size, N] remember highest score of each path
        states[t] = np.argmax(
            weighted_scores, axis=1
        )  # [batch_size, N] remember index of best path, should be repeated for padding vals

    tokens = np.zeros((T, batch_size), dtype=np.intp)
    tokens[T - 1] = np.argmax(trellis[T - 1], axis=1)  # [batch_size]

    for t in range(T - 1, 0, -1):
        tokens[t - 1] = states[t, np.arange(batch_size), tokens[t]]  # [batch_size]

    return tokens.T  # [batch_size, T]


def viterbi_dense(
    p_emit: np.ndarray, p_trans: np.ndarray, p_trans0: Optional[np.ndarray] = None, mask: Optional[np.ndarray] = None
) -> np.ndarray:

    """Viterbi algorithm for finding the optimal path.
    One square transition matrix can be specified.

    T: max sequence length
    N: vocab size
    batch_size: to vectorize

    p_emit: masked emission scores [batch_size, T, N] float
    p_trans: transition scores [N, N] float
    p_trans0: initial transition scores [N] float
    mask: mask out padding values in transitions [batch_size, T] float
    """

    batch_size, T, N = p_emit.shape

    if mask is None:
        mask = np.ones((batch_size, T), dtype=p_trans.dtype)

    if p_trans0 is None:
        p_trans0 = np.zeros(N, dtype=p_emit.dtype)

    return _viterbi_dense_masked(p_emit, p_trans, p_trans0, mask)


# @opjit() # doesn't work atm because numba cannot store arbitrary elements in lists I think
def viterbi_sparse(p_emit: Sequence[np.ndarray], p_trans: Sequence[np.ndarray]) -> np.ndarray:

    """Viterbi algorithm for finding the optimal path.
    The number of emission probabilities per index can vary
    and a separate matrix can be specified for each transition.

    p_emit: Sequence of [x] matrices, where x can vary for every entry
    p_trans: Sequence of [y, z] matrices, where y and z can vary for every entry

    todo: using `Iterable`s instead of Sequence`s should be possible.
    """

    T = len(p_emit)

    assert T - 1 == len(p_trans)

    trellis = [p_emit[0]]
    states = [None]

    for t in range(1, T):
        weighted_scores = trellis[-1][:, None] + p_trans[t - 1]  # [x, y] # scores and p_trans broadcasted
        max_scores = np.amax(weighted_scores, axis=0)  # [y]
        trellis.append(np.add(max_scores, p_emit[t]))  # [y] remember highest score of each path
        states.append(np.argmax(weighted_scores, axis=0))  # [y] remember index of best path

    assert len(trellis) == T and len(states) == T

    tokens = [None] * T  # [T]
    tokens[-1] = np.argmax(trellis[-1], axis=0)  # []

    for t in range(T - 1, 0, -1):
        tokens[t - 1] = states[t][tokens[t]]  # []

    return tokens


_bit_counts = np.array([int(bin(x).count("1")) for x in range(256)]).astype(np.uint8)


def hamming_dist_packed(a: np.ndarray, b: np.ndarray, axis: Optional[int] = -1) -> np.ndarray:
    return np.sum(_bit_counts[np.bitwise_xor(a, b)], axis=axis)


def get_num_chunks(shape: np.ndarray, chunksize: np.ndarray) -> int:
    return np.prod(np.ceil(shape / chunksize).astype(np.int_))


def broadcast_shapes(*shapes: Tuple[int, ...]) -> Tuple[int, ...]:
    """np.broadcast_shapes requires `numpy==1.20.0`,
    which is not available for `python < 3.7`.
    """

    arrays = [np.empty(shape) for shape in shapes]
    return np.broadcast(*arrays).shape


def hamming_dist_packed_chunked(
    a: np.ndarray, b: np.ndarray, chunksize: Tuple[int, ...], axis: Optional[int] = -1
) -> Iterator[Tuple[Tuple[int, ...], np.ndarray]]:

    outshape = broadcast_shapes(a.shape, b.shape)
    select_broadcasted_axis = slice(0, 1)

    if len(outshape) - len(chunksize) != 1:
        raise ValueError("Length of `chunksize` must be one less the number of input dimensions")

    if len(outshape) == 2:
        for x in range(0, outshape[0], chunksize[0]):
            if a.shape[0] != outshape[0]:
                aix = select_broadcasted_axis
            else:
                aix = slice(x, x + chunksize[0])

            if b.shape[0] != outshape[0]:
                bix = select_broadcasted_axis
            else:
                bix = slice(x, x + chunksize[0])

            yield (x,), hamming_dist_packed(a[aix, :], b[bix, :], axis=axis)

    elif len(outshape) == 3:
        for x in range(0, outshape[0], chunksize[0]):
            for y in range(0, outshape[1], chunksize[1]):

                if a.shape[0] != outshape[0]:
                    aix = select_broadcasted_axis
                else:
                    aix = slice(x, x + chunksize[0])

                if b.shape[0] != outshape[0]:
                    bix = select_broadcasted_axis
                else:
                    bix = slice(x, x + chunksize[0])

                if a.shape[1] != outshape[1]:
                    aiy = select_broadcasted_axis
                else:
                    aiy = slice(y, y + chunksize[1])

                if b.shape[1] != outshape[1]:
                    biy = select_broadcasted_axis
                else:
                    biy = slice(y, y + chunksize[1])

                yield (x, y), hamming_dist_packed(a[aix, aiy, :], b[bix, biy, :], axis=axis)

    else:
        raise ValueError("Input must either be 2 or 3 dimensional")


def hamming_dist(a: np.ndarray, b: np.ndarray, axis: Optional[int] = -1) -> np.ndarray:
    return np.count_nonzero(a != b, axis=axis)


def center_of_mass_2d(arr: np.ndarray, dtype=np.float32) -> np.ndarray:
    """Batched center of mass calculation of 2d arrays
    `arr`: [..., x, y]
    """

    total = np.sum(arr, axis=(-1, -2))
    grids = np.ogrid[[slice(0, i) for i in arr.shape[-2:]]]
    results = np.array([np.sum(arr * grid.astype(dtype), axis=(-1, -2)) / total for grid in grids], dtype=dtype).T

    return results
