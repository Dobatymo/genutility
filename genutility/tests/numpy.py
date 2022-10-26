from __future__ import generator_stop

import numpy as np

from genutility.benchmarks.numpy import bincount_batch_2
from genutility.math import shannon_entropy as shannon_entropy_python
from genutility.numpy import (
    batch_inner,
    batch_outer,
    batch_vTAv,
    batchtopk,
    bincount_batch,
    center_of_mass_2d,
    decompress,
    hamming_dist,
    hamming_dist_packed,
    hamming_dist_packed_chunked,
    is_rgb,
    is_square,
    logtrace,
    remove_color,
    rgb_to_hsi,
    sequence_mask,
    shannon_entropy,
    shiftedexp,
    sliding_window_2d,
    stochastic,
    unblock,
    unblock2d,
    viterbi_dense,
    viterbi_sparse,
)
from genutility.test import MyTestCase, parametrize, repeat

RED = [255, 0, 0]
GREEN = [0, 255, 0]
BLUE = [0, 0, 255]

YELLOW = [255, 255, 0]

BLACK = [0, 0, 0]
GRAY = [128, 128, 128]
WHITE = [255, 255, 255]


def list_mapget(item, it):
    return [i[item] for i in it]


class ViterbiTest(MyTestCase):
    def test_viterbi_sparse_emit(self):
        p_emit = [np.array([1.0, 2.0]), np.array([4.0, 3.0])]
        p_trans = [np.array([[0.0, 0.0], [0.0, 0.0]])]

        truth = [1, 0]
        result = viterbi_sparse(p_emit, p_trans)
        self.assertEqual(truth, result)

    def test_viterbi_sparse_trans(self):
        p_emit = [np.array([0.0, 1.0]), np.array([0.0, 0.0])]
        p_trans = [np.array([[0.0, 1.0], [1.0, 0.0]])]

        truth = [1, 0]
        result = viterbi_sparse(p_emit, p_trans)
        self.assertEqual(truth, result)

    def test_viterbi_sparse_combined(self):
        # 1
        p_emit = [np.array([0.5, 0.5]), np.array([0.1, 0.9])]
        p_trans = [np.array([[0.2, 0.8], [0.7, 0.3]])]

        truth = [0, 1]
        result = viterbi_sparse(p_emit, p_trans)
        self.assertEqual(truth, result)

        # 2
        p_emit = [np.array([0.6, 0.4]), np.array([0.3, 0.7])]
        p_trans = [np.array([[0.2, 0.8], [0.7, 0.3]])]

        truth = [0, 1]
        result = viterbi_sparse(p_emit, p_trans)
        self.assertEqual(truth, result)

    def test_viterbi_dense_emit(self):
        p_emit = np.array([[[1.0, 2.0], [4.0, 3.0]]])
        p_trans = np.array([[0.0, 0.0], [0.0, 0.0]])
        p_trans0 = np.array([0.0, 0.0])

        # trellis[0]: [ [1., 2.] ]
        # states[0]: [None]
        # scores: [ [[1.], [2.]] ]
        # weighted_scores = [ [[1., 1.], [2., 2.]] ]
        # max_scores = [ [2., 2.] ]
        # trellis[1] = [ [6., 5.] ]
        # states[1] = [ [1, 1] ]
        # tokens[1] = [0]
        # tokens[0] = [1]

        truth = np.array([[1, 0]])
        result = viterbi_dense(p_emit, p_trans, p_trans0)
        np.testing.assert_equal(truth, result)

    def test_viterbi_dense_trans(self):
        p_emit = np.array([[[0.0, 0.0], [0.0, 0.0]]])
        p_trans = np.array([[0.0, 1.0], [1.0, 0.0]])
        p_trans0 = np.array([0.0, 1.0])

        # trellis[0]: [ [0., 1.] ]
        # states[0]: [None]
        # scores: [ [[0.], [1.]] ]
        # weighted_scores = [ [[0., 1.], [2., 0.]] ]
        # max_scores = [ [2., 1.] ]
        # trellis[1] = [ [2., 1.] ]
        # states[1] = [ [1, 0] ]
        # tokens[1] = [0]
        # tokens[0] = [1]

        truth = np.array([[1, 0]])
        result = viterbi_dense(p_emit, p_trans, p_trans0)
        np.testing.assert_equal(truth, result)

    def test_viterbi_dense_combined_with_batch(self):
        # 1
        p_emit = np.array([[[0.5, 0.5], [0.1, 0.9]], [[0.6, 0.4], [0.3, 0.7]]])
        p_trans = np.array([[0.2, 0.8], [0.7, 0.3]])
        p_trans0 = np.array([0.4, 0.6])

        # trellis[0]: [[0.9, 1.1], [1.0, 1.0]]
        # states[0]: [None]
        # scores: [[[0.9], [1.1]], [[1.0], [1.0]]]
        # weighted_scores = [ [[1.1, 1.7], [1.8, 1.4]], [[1.2, 1.8], [1.7, 1.3]] ]
        # max_scores = [[1.8, 1.7], [1.7, 1.8]]
        # trellis[1] = [[1.9, 2.6], [2.0, 2.5]]
        # states[1] = [[1, 0], [1, 0]]
        # tokens[1] = [1, 1]
        # tokens[0] = [0, 0]

        truth = np.array([[0, 1], [0, 1]])
        result = viterbi_dense(p_emit, p_trans, p_trans0)
        np.testing.assert_equal(truth, result)

    def test_viterbi_dense_combined_with_mask(self):
        # 1
        p_emit = np.array([[[0.45, 0.55], [0.0, 0.0]]])
        p_trans = np.array([[0.1, 0.9], [0.6, 0.4]])
        p_trans0 = np.array([0.45, 0.55])
        sequence_lengths = np.array([1])
        mask = sequence_mask(sequence_lengths, 2, dtype=p_trans.dtype)  # [batch_size, T]

        # UNMASKED VERSION

        # trellis[0]: [ [0.9, 1.1] ]
        # states[0]: [None]
        # scores: [ [[0.9], [1.1]] ]
        # weighted_scores = [ [[1.0, 1.8], [1.7, 1.5]] ]
        # max_scores = [ [1.7, 1.8] ]
        # trellis[1] = [ [1.7, 1.8] ]
        # states[1] = [ [1, 0] ]
        # tokens[1] = [1]
        # tokens[0] = [0]

        truth = np.array([[1, 0]])
        result = viterbi_dense(p_emit, p_trans, p_trans0, mask)
        np.testing.assert_equal(truth, result)


class NumpyTest(MyTestCase):
    @parametrize(
        ([[RED, GREEN], [BLUE, GRAY]], 1, [[RED, GREEN], [BLUE, GRAY]]),
        ([[RED, GREEN], [BLUE, GRAY]], 0, [[WHITE, WHITE], [WHITE, GRAY]]),
    )
    def test_remove_color(self, img, ratio, truth):
        img = np.array(img)
        remove_color(img, ratio)  # inplace
        truth = np.array(truth)
        self.assertTrue(np.array_equal(truth, img))

    @parametrize(
        ([], False),
        ([0, 0, 0], True),
        ([[0, 0, 0]], True),
        ([[0, 0, 0], [0, 0, 0]], True),
        ([[0], [0], [0]], False),
    )
    def test_is_rgb(self, arr, truth):
        arr = np.array(arr)
        result = is_rgb(arr)
        self.assertEqual(truth, result)

    @parametrize(
        ([], False),
        ([[]], False),  # fixme: what about this one?
        ([[0]], True),
        ([[0, 0], [0, 0]], True),
        ([[0, 0]], False),
        ([[0], [0]], False),
    )
    def test_is_square(self, arr, truth):
        arr = np.array(arr)
        result = is_square(arr)
        self.assertEqual(truth, result)

    @parametrize(
        ([[0, 0], [0, 0]], [0, 0], 0),
        ([[1, 2], [3, 4]], [5, 6], 319),
        ([[[0, 0], [0, 0]]], [[0, 0]], [0]),
        ([[[1, 2], [3, 4]]], [[5, 6]], [319]),
        ([[[0, 0], [0, 0]], [[1, 2], [3, 4]]], [[0, 0], [5, 6]], [0, 319]),
    )
    def test_batch_vTAv(self, A, v, truth):
        A = np.array(A)
        v = np.array(v)
        result = batch_vTAv(A, v)
        np.testing.assert_equal(truth, result)

    @parametrize(
        ([[1, 2], [3, 4]], [5], 250),
        ([[[0, 0], [0, 0]], [[1, 2], [3, 4]]], [[5, 6]], [0, 319]),
    )
    def test_batch_vTAv_broadcast(self, A, v, truth):
        A = np.array(A)
        v = np.array(v)
        result = batch_vTAv(A, v)
        np.testing.assert_equal(truth, result)

    @parametrize(
        ([], []),
    )
    def test_batch_vTAv_valueerror(self, A, v):
        A = np.array(A)
        v = np.array(v)
        with self.assertRaises(ValueError):
            batch_vTAv(A, v)

    @parametrize(
        ([], [], []),
        ([0, 0], [0, 0], 0),
        ([1, 2], [3, 4], 11),
        ([[0, 0]], [[0, 0]], [0]),
        ([[1, 2]], [[3, 4]], [11]),
        ([[0, 0], [1, 2]], [[0, 0], [3, 4]], [0, 11]),
    )
    def test_batch_inner(self, A, B, truth):
        A = np.array(A)
        B = np.array(B)
        result = batch_inner(A, B)
        np.testing.assert_equal(truth, result)

    @parametrize(
        ([1, 2], [2]),
        ([[0, 0], [1, 2]], [[3, 4]]),
    )
    def test_batch_inner_valueerror(self, A, B):
        A = np.array(A)
        B = np.array(B)
        with self.assertRaises(ValueError):
            batch_inner(A, B)

    @parametrize(
        ([], [], np.empty(shape=(0, 0))),
        ([0, 0], [0, 0], [[0, 0], [0, 0]]),
        ([1, 2], [3, 4], [[3, 4], [6, 8]]),
        ([1, 2], [3], [[3], [6]]),
        ([[0, 0], [1, 2]], [[0, 0], [3, 4]], [[[0, 0], [0, 0]], [[3, 4], [6, 8]]]),
    )
    def test_batch_outer(self, A, B, truth):
        A = np.array(A)
        B = np.array(B)
        result = batch_outer(A, B)
        np.testing.assert_equal(truth, result)

    @parametrize(
        ([[0], [0]], [0]),
    )
    def test_batch_outer_valueerror(self, A, B):
        A = np.array(A)
        B = np.array(B)
        with self.assertRaises(ValueError):
            batch_outer(A, B)

    @parametrize(
        ([[1, 1], [1, 1]], 0.0),
        ([[1, 2], [3, 4]], 1.3862943611198906),
        ([[[1, 1], [1, 1]], [[1, 2], [3, 4]]], [0.0, 1.3862943611198906]),
    )
    def test_logtrace(self, arr, truth):
        arr = np.array(arr)
        result = logtrace(arr)
        np.testing.assert_allclose(truth, result)

    @parametrize(
        ([], []),
        ([0, 0], [1.0, 1.0]),
        ([1, 2], [0.36787944117144233, 1.0]),
        ([[0, 0], [1, 2]], [[1.0, 1.0], [0.36787944117144233, 1.0]]),
    )
    def test_shiftedexp(self, pvals, truth):
        pvals = np.array(pvals)
        result = shiftedexp(pvals)
        np.testing.assert_allclose(truth, result)

    @parametrize(([1 / 3, 2 / 3], 0.9182958340544896), ([0.5, 0.2, 0.1, 0.1, 0.1], 1.9609640474436814))
    def test_shannon_entropy(self, probabilities, truth):
        result = shannon_entropy(probabilities)
        truth = np.array(truth)
        self.assertAlmostEqual(truth, result)

        result_python = shannon_entropy_python(probabilities)
        self.assertAlmostEqual(result_python, result)

    @parametrize(
        ([0.0, 0.0, 0.0], [0.0, 0.0, 0.0]),  # 000000
        ([1.0, 1.0, 1.0], [0.0, 0.0, 1.0]),  # #FFFFFF
        ([0.628, 0.643, 0.142], [np.radians(61.5), 0.699, 0.471]),  # A0A424
        ([0.255, 0.104, 0.918], [np.radians(250.0), 0.756, 0.426]),  # 411BEA
    )
    def test_rgb_to_hsi(self, img, truth):
        """See: https://en.wikipedia.org/wiki/HSL_and_HSV#Examples (H_2, S_HSI, I)"""

        img, truth = np.array(img), np.array(truth)
        result = rgb_to_hsi(img)
        self.assertTrue(np.allclose(truth, result, atol=0, rtol=1e-3), msg=str(result))

    @parametrize(
        ([[0, 1], [2, 3]], (1, 1), (1, 1), [[[0]], [[1]], [[2]], [[3]]]),
        (
            np.arange(9).reshape(3, 3),
            (2, 2),
            (1, 1),
            [[[0, 1], [3, 4]], [[1, 2], [4, 5]], [[3, 4], [6, 7]], [[4, 5], [7, 8]]],
        ),
    )
    def test_sliding_window_2d(self, image, ws, ss, truth):
        image, truth = np.array(image), np.array(truth)
        result = np.array(list(sliding_window_2d(image, ws, ss)))
        self.assertTrue(np.array_equal(truth, result))

    @parametrize(
        ([[1, 2], [4, 3]], None, -1, False, [[1, 2], [3, 4]]),
        ([[1, 2], [4, 3]], None, -1, True, [[2, 1], [4, 3]]),
        ([[1, 2, 3, 4], [8, 7, 6, 5], [9, 10, 11, 12]], 1, -1, False, [[1], [5], [9]]),
        ([[1, 2, 3, 4], [8, 7, 6, 5], [9, 10, 11, 12]], 1, -1, True, [[4], [8], [12]]),
        ([[1, 2, 3, 4], [8, 7, 6, 5], [9, 10, 11, 12]], 2, -1, False, [[1, 2], [5, 6], [9, 10]]),
        ([[1, 2, 3, 4], [8, 7, 6, 5], [9, 10, 11, 12]], 2, -1, True, [[4, 3], [8, 7], [12, 11]]),
        # ([[9,2,3,12], [5,6,7,4], [1,10,11,8]], 2, 0, [[5,9], [6,10], [7,11], [8,12]]),
    )
    def test_batchtopk(self, arr, k, axis, reverse, truth):
        arr, truth = np.array(arr), np.array(truth)
        indices, probs = batchtopk(arr, k, axis, reverse)
        np.testing.assert_equal(truth, probs)

    @parametrize(
        ([[1, 2], [3, 4]], 1, 1, {"blocksize": False}, [[1, 2, 3, 4]]),
        ([[1, 2], [3, 4]], 1, 1, {"blocksize": True}, [[1], [2], [3], [4]]),
        (
            [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12], [13, 14, 15, 16]],
            2,
            2,
            {"blocksize": False},
            [[1, 2, 5, 6], [3, 4, 7, 8], [9, 10, 13, 14], [11, 12, 15, 16]],
        ),
        (
            [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12], [13, 14, 15, 16]],
            2,
            2,
            {"blocksize": True},
            [[1, 2, 5, 6], [3, 4, 7, 8], [9, 10, 13, 14], [11, 12, 15, 16]],
        ),
        (
            [[[1, 2, 3], [2, 3, 4]], [[3, 4, 5], [4, 5, 6]]],
            1,
            1,
            {"axis1": 1, "axis2": 0, "blocksize": False},
            [[[1, 2, 3], [2, 3, 4], [3, 4, 5], [4, 5, 6]]],
        ),
        (
            [[[1, 2, 3], [2, 3, 4]], [[3, 4, 5], [4, 5, 6]]],
            1,
            1,
            {"axis1": 1, "axis2": 0, "blocksize": True},
            [[[1, 2, 3]], [[2, 3, 4]], [[3, 4, 5]], [[4, 5, 6]]],
        ),
    )
    def test_unblock(self, arr, a, b, kwargs, truth):
        arr, truth = np.array(arr), np.array(truth)
        result = unblock(arr, a, b, **kwargs)
        np.testing.assert_equal(truth, result)

    @parametrize(
        ([[1, 2], [3, 4]], 1, 1, False, [[1, 2, 3, 4]]),
        ([[1, 2], [3, 4]], 1, 1, True, [[1], [2], [3], [4]]),
        (
            [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12], [13, 14, 15, 16]],
            2,
            2,
            False,
            [[1, 2, 5, 6], [3, 4, 7, 8], [9, 10, 13, 14], [11, 12, 15, 16]],
        ),
        (
            [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12], [13, 14, 15, 16]],
            2,
            2,
            True,
            [[1, 2, 5, 6], [3, 4, 7, 8], [9, 10, 13, 14], [11, 12, 15, 16]],
        ),
        ([[[1, 2, 3], [2, 3, 4]], [[3, 4, 5], [4, 5, 6]]], 1, 1, False, [[[1, 2, 3], [2, 3, 4], [3, 4, 5], [4, 5, 6]]]),
        (
            [[[1, 2, 3], [2, 3, 4]], [[3, 4, 5], [4, 5, 6]]],
            1,
            1,
            True,
            [[[1, 2, 3]], [[2, 3, 4]], [[3, 4, 5]], [[4, 5, 6]]],
        ),
    )
    def test_unblock2d(self, arr, a, b, blocksize, truth):
        arr, truth = np.array(arr), np.array(truth)
        result = unblock2d(arr, a, b, blocksize)
        np.testing.assert_equal(truth, result)

    @parametrize(
        ([], [], 0, []),
        ([True], [1], 0, [1]),
        ([False], [], 0, [0]),
        ([True, False, True], [1, 3], 0, [1, 0, 3]),
    )
    def test_decompress(self, selectors, data, default, truth):
        selectors, data, truth = np.array(selectors, dtype=bool), np.array(data), np.array(truth)
        result = decompress(selectors, data, default)
        np.testing.assert_equal(truth, result)

    @parametrize(
        ([[1, 2], [3, 4]], 0, [[0, 1, 1, 0, 0], [0, 0, 0, 1, 1]]),
        ([[1, 2], [3, 4]], 8, [[0, 1, 1, 0, 0, 0, 0, 0], [0, 0, 0, 1, 1, 0, 0, 0]]),
        ([[0]], 0, [[1]]),
    )
    def test_bincount_batch(self, arr, minlength, truth):
        arr, truth = np.array(arr), np.array(truth)

        result = bincount_batch(arr, minlength=minlength)
        np.testing.assert_equal(truth, result)

        result = bincount_batch_2(arr, minlength=minlength)
        np.testing.assert_equal(truth, result)

    @repeat(3)
    def test_bincount_batch_random(self):
        arr = np.random.randint(0, 10000, (1000, 1000))

        result_1 = bincount_batch(arr)
        result_2 = bincount_batch_2(arr)
        np.testing.assert_equal(result_1, result_2)

    def test_stochastic(self):
        x = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
        truth = np.array([[1 / 6, 2 / 6, 3 / 6], [4 / 15, 5 / 15, 6 / 15], [7 / 24, 8 / 24, 9 / 24]])
        result = stochastic(x)
        np.testing.assert_allclose(truth, result)

    def test_sequence_mask(self):
        x = []
        truth = np.array([], dtype=np.bool_)
        result = sequence_mask(x)
        np.testing.assert_equal(truth, result)
        self.assertEqual(truth.dtype, result.dtype)

        x = [3, 1, 2]
        truth = np.array([[True, True, True], [True, False, False], [True, True, False]])
        result = sequence_mask(x)
        np.testing.assert_equal(truth, result)
        self.assertEqual(truth.dtype, result.dtype)

    def test_hamming_dist(self):
        a = np.unpackbits(np.array([0, 0, 0, 255, 255, 255], dtype=np.uint8)).reshape(3, 16)
        b = np.unpackbits(np.array([0, 1, 0, 2, 2, 3], dtype=np.uint8)).reshape(3, 16)

        truth = np.array([1, 7, 13])
        result = hamming_dist(a, b)
        np.testing.assert_equal(truth, result)

        truth = np.array([[1, 7, 15], [1, 7, 15], [3, 7, 13]])
        result = hamming_dist(a[None, :], b[:, None])
        np.testing.assert_equal(truth, result)

    def test_hamming_dist_packed(self):
        a = np.array([[0, 0], [0, 255], [255, 255]])
        b = np.array([[0, 1], [0, 2], [2, 3]])

        truth = np.array([1, 7, 13])
        result = hamming_dist_packed(a, b)
        np.testing.assert_equal(truth, result)

        truth = np.array([[1, 7, 15], [1, 7, 15], [3, 7, 13]])
        result = hamming_dist_packed(a[None, :], b[:, None])
        np.testing.assert_equal(truth, result)

    def test_hamming_dist_packed_chunked(self):
        a = np.array([[0, 0], [0, 255], [255, 255]])
        b = np.array([[0, 1], [0, 2], [2, 3]])
        c = np.array([[0, 1]])

        # 1d one chunk
        truth = [np.array([1, 7, 13])]
        result = list_mapget(1, hamming_dist_packed_chunked(a, b, (10,)))
        np.testing.assert_equal(truth, result)

        # 1d clean divides
        truth = [np.array([1]), np.array([7])]
        result = list_mapget(1, hamming_dist_packed_chunked(a[0:2], b[0:2], (1,)))
        np.testing.assert_equal(truth, result)

        # 1d unclean divides
        truth = [np.array([1, 7]), np.array([13])]
        result = list_mapget(1, hamming_dist_packed_chunked(a, b, (2,)))
        np.testing.assert_equal(truth, result)

        # 1d broadcasted unclean divides
        truth = [np.array([1, 7]), np.array([15])]
        result = list_mapget(1, hamming_dist_packed_chunked(a, c, (2,)))
        np.testing.assert_equal(truth, result)

        # 2d broadcasted one chunk
        truth = [np.array([[1, 7, 15], [1, 7, 15], [3, 7, 13]])]
        result = list_mapget(1, hamming_dist_packed_chunked(a[None, :], b[:, None], (10, 10)))
        np.testing.assert_equal(truth, result)

        # 2d broadcasted clean divides
        truth = [np.array([[1]]), np.array([[7]]), np.array([[1]]), np.array([[7]])]
        result = list_mapget(1, hamming_dist_packed_chunked(a[None, 0:2], b[0:2, None], (1, 1)))
        np.testing.assert_equal(truth, result)

        # 2d broadcasted unclean divides
        truth = [np.array([[1, 7], [1, 7]]), np.array([[15], [15]]), np.array([[3, 7]]), np.array([[13]])]
        result = list_mapget(1, hamming_dist_packed_chunked(a[None, :], b[:, None], (2, 2)))
        np.testing.assert_equal(truth, result)

    @parametrize(
        ([[]], np.float64, [np.nan, np.nan]),
        ([[0]], np.float64, [np.nan, np.nan]),
        ([[1]], np.float64, [0, 0]),
        ([[1, 0], [0, 0]], np.float64, [0, 0]),
        ([[0, 1], [0, 0]], np.float64, [0, 1]),
        ([[0, 0], [1, 0]], np.float64, [1, 0]),
        ([[0, 0], [0, 1]], np.float64, [1, 1]),
        ([[[0, 0], [0, 1]], [[1, 1], [1, 1]]], np.float32, [[1, 1], [0.5, 0.5]]),
    )
    def test_center_of_mass_2d(self, arr, dtype, truth):
        arr = np.array(arr)
        truth = np.array(truth, dtype=dtype)
        result = center_of_mass_2d(arr, dtype=dtype)
        np.testing.assert_array_equal(truth, result)
        self.assertEqual(truth.dtype, result.dtype)


if __name__ == "__main__":
    import unittest

    unittest.main()
