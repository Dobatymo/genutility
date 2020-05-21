from timeit import repeat

benchmarks = {
	"all_equal": {
		"all-different": {
			"stmt": "all_equal(range(100000))",
			"setup": "from genutility.iter import all_equal",
		},
		"all-same": {
			"stmt": "all_equal(range(100000))",
			"setup": "from itertools import repeat; from genutility.iter import all_equal",
		}
	}
}

if __name__ == "__main__":

	for funcname, benchs in benchmarks.items():
		for benchname, kwargs in benchs.items():
			print(funcname, benchname, min(repeat(**kwargs)))
