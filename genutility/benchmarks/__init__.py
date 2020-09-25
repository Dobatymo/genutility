from __future__ import absolute_import, division, print_function, unicode_literals

from argparse import ArgumentParser
from timeit import repeat


def run(benchmarks):
	# type: (dict, ) -> None

	parser = ArgumentParser()
	parser.add_argument("testcases", nargs="*")
	args = parser.parse_args()

	if args.testcases:
		for funcname in args.testcases:
			if "." in funcname:
				funcname, benchname = funcname.split(".")
				kwargs = benchmarks[funcname][benchname]
				print(funcname, benchname, min(repeat(**kwargs)))

			else:
				benchs = benchmarks[funcname]
				for benchname, kwargs in benchs.items():
					print(funcname, benchname, min(repeat(**kwargs)))

	else:
		for funcname, benchs in benchmarks.items():
			for benchname, kwargs in benchs.items():
				print(funcname, benchname, min(repeat(**kwargs)))
