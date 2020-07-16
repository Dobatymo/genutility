from __future__ import absolute_import, division, print_function, unicode_literals

def pop_many_2(seq, func):
	# type: (MutableSequence[T], Callable) -> Iterator[T]

	""" pop()s a values from `seq` where func(value) is true.
	"""

	i = 0
	while i < len(seq):
		if func(seq[i]):
			yield seq.pop(i)
		else:
			i += 1

benchmarks = {
	"pop_many": {
		"all": {
			"stmt": "list(pop_many(list(range(100000)), lambda x: True))",
			"setup": "from genutility.sequence import pop_many",
			"number": 100,
		},
		"none": {
			"stmt": "list(pop_many(list(range(100000)), lambda x: False))",
			"setup": "from genutility.sequence import pop_many",
			"number": 100,
		},
	},
	"pop_many_2": {
		"all": {
			"stmt": "list(pop_many_2(list(range(100000)), lambda x: True))",
			"setup": "from __main__ import pop_many_2",
			"number": 100,
		},
		"none": {
			"stmt": "list(pop_many_2(list(range(100000)), lambda x: False))",
			"setup": "from __main__ import pop_many_2",
			"number": 100,
		},
	},
}

if __name__ == "__main__":
	"""
	pop_many all 5.294865000000001
	pop_many none 2.5507518000000005
	pop_many_2 all 148.57841040000005
	pop_many_2 none 3.891317099999924
	"""

	from genutility.benchmarks import run
	run(benchmarks)
