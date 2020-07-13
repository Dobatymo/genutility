import numpy as np

#image = np.random.randint(0, 255, (1000, 1000))
#list(sliding_window_2d(image, (100, 100), (1, 1))) # warmup
#print(min(timeit.repeat('list(sliding_window_2d(image, (100, 100), (1, 1)))', number=10, repeat=5, globals=globals())))

single_arr = np.random.uniform(0, 1, (100, 100)).astype(np.float64)
batch_arr = np.random.uniform(0, 1, (100, 100, 100)).astype(np.float64)
batch_out = np.empty(100, dtype=np.float64)

benchmarks = {
	"logtrace": {
		"logtrace-numpy": {
			"stmt": "logtrace(single_arr)",
			"setup": "from genutility.numpy import logtrace; from __main__ import single_arr",
			"number": 1000,
		},
		"logtrace-cython": {
			"stmt": "logtrace(single_arr)",
			"setup": "from unclog.math import logtrace; from __main__ import single_arr",
			"number": 1000,
		},
	},
	"logtrace-batch": {
		"logtrace-numpy": {
			"stmt": "logtrace(batch_arr)",
			"setup": "from genutility.numpy import logtrace; from __main__ import batch_arr",
			"number": 1000,
		},
		"logtrace-cython": {
			"stmt": "logtrace_batch(batch_arr, batch_out)",
			"setup": "from unclog.math import logtrace_batch; from __main__ import batch_arr, batch_out",
			"number": 1000,
		},
	},
}

if __name__ == "__main__":

	from timeit import repeat

	for funcname, benchs in benchmarks.items():
		for benchname, kwargs in benchs.items():
			print(funcname, benchname, min(repeat(**kwargs)))
