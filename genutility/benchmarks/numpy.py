from __future__ import absolute_import, division, print_function, unicode_literals

import numpy as np
from numba import prange
from genutility.numba import opjit

#image = np.random.randint(0, 255, (1000, 1000))
#list(sliding_window_2d(image, (100, 100), (1, 1))) # warmup
#print(min(timeit.repeat('list(sliding_window_2d(image, (100, 100), (1, 1)))', number=10, repeat=5, globals=globals())))

single_arr = np.random.uniform(0, 1, (100, 100)).astype(np.float64)
batch_arr = np.random.uniform(0, 1, (100, 100, 100)).astype(np.float64)
batch_out = np.empty(100, dtype=np.float64)

bincount_batch_arr = np.random.randint(0, 10000, (1000, 1000))

def bincount_batch_2(x, axis=-1, minlength=0):

	""" Only slightly faster than bincount-batch.
		Only supports 2D arrays with axis=-1 however.
	"""

	# based on: https://stackoverflow.com/a/46256361

	if axis != -1:
		raise ValueError("Only bincount in the last axis is supported")

	if x.shape[axis] == 0:
		raise ValueError("Specified axis of x cannot be 0")

	N = max(minlength, x.max() + 1)

	offset = x + np.arange(x.shape[0])[:,None] * N

	return np.bincount(offset.ravel(), minlength=x.shape[0] * N).reshape(-1, N)

@opjit(parallel=True)
def _bincount_batch_3(arr, out):
	B, X = arr.shape
	for b in prange(B):
		for x in range(X):
			out[b, arr[b, x]] += 1

def bincount_batch_3(arr, axis=-1, minlength=0):
	N = max(minlength, arr.max() + 1)

	if axis != -1:
		raise ValueError("Only bincount in the last axis is supported")

	if arr.shape[axis] == 0:
		raise ValueError("Specified axis of arr cannot be 0")

	B = arr.shape[0]
	out = np.zeros((B, N), dtype=np.int)

	_bincount_batch_3(arr, out)

	return out

benchmarks = {
	"logtrace": {
		"logtrace-numpy": {
			"stmt": "logtrace(single_arr)",
			"setup": "from genutility.numpy import logtrace; from __main__ import single_arr",
			"number": 10000,
		},
		"logtrace-cython": {
			"stmt": "logtrace(single_arr)",
			"setup": "from unclog.math import logtrace; from __main__ import single_arr",
			"number": 10000,
		},
	},
	"logtrace-batch": {
		"logtrace-numpy": {
			"stmt": "logtrace(batch_arr)",
			"setup": "from genutility.numpy import logtrace; from __main__ import batch_arr",
			"number": 10000,
		},
		"logtrace-cython": {
			"stmt": "logtrace_batch(batch_arr, batch_out)",
			"setup": "from unclog.math import logtrace_batch; from __main__ import batch_arr, batch_out",
			"number": 10000,
		},
	},
	"bincount-batch": {
		"bincount_batch": {
			"stmt": "bincount_batch(bincount_batch_arr)",
			"setup": "from genutility.numpy import bincount_batch; from __main__ import bincount_batch_arr",
			"number": 100,
		},
		"bincount_batch_2": {
			"stmt": "bincount_batch_2(bincount_batch_arr)",
			"setup": "from __main__ import bincount_batch_2, bincount_batch_arr",
			"number": 100,
		},
		"bincount_batch_3": {
			"stmt": "bincount_batch_3(bincount_batch_arr)",
			"setup": "from __main__ import bincount_batch_3, bincount_batch_arr",
			"number": 100,
		},
		"bincount_batch_4": {
			"stmt": "bincount_batch(bincount_batch_arr)",
			"setup": "from unclog.math import bincount_batch; from __main__ import bincount_batch_arr",
			"number": 100,
		},
	}
}

if __name__ == "__main__":
	from genutility.benchmarks import run
	run(benchmarks)
