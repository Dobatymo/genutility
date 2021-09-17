import numpy as np

from genutility.datastructures.sparse_matrix import VariableRowMatrix

num = 9999999
height = 1000
width = 100

lol = np.arange(height*width).reshape((height, width)).tolist()
d = dict()
for i, col in enumerate(lol):
	for j, val in enumerate(col):
		d[i, j] = val

sm = VariableRowMatrix.from_list_of_lists(lol)

xs = np.random.randint(0, height, num)
ys = np.random.randint(0, width, num)

def index_lol():
	for x, y in zip(xs, ys):
		lol[x][y]

def index_sm():
	for x, y in zip(xs, ys):
		sm[x, y]

def index_sm_2():
	for ind in zip(xs, ys):
		sm[ind]

def index_d():
	for x, y in zip(xs, ys):
		d[x, y]

def index_d_2():
	for ind in zip(xs, ys):
		d[ind]

benchmarks = {
	"VariableRowMatrix": {
		"index_lol": {
			"stmt": "index_lol()",
			"setup": "from __main__ import index_lol",
			"number": 3,
		},
		"index_sm": {
			"stmt": "index_sm()",
			"setup": "from __main__ import index_sm",
			"number": 3,
		},
		"index_sm_2": {
			"stmt": "index_sm_2()",
			"setup": "from __main__ import index_sm_2",
			"number": 3,
		},
		"index_d": {
			"stmt": "index_d()",
			"setup": "from __main__ import index_d",
			"number": 3,
		},
		"index_d_2": {
			"stmt": "index_d_2()",
			"setup": "from __main__ import index_d_2",
			"number": 3,
		},
	}
}

if __name__ == "__main__":
	"""
	all_equal index_lol 16.247700299999998
	all_equal index_sm 41.017197399999986
	all_equal index_sm_2 35.80030429999999
	all_equal index_d 67.36033410000005
	all_equal index_d_2 74.64404740000009
	"""

	from genutility.benchmarks import run
	run(benchmarks)
