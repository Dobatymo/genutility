from __future__ import absolute_import, division, print_function, unicode_literals
from builtins import input, range

import os, sys, os.path, shlex
from functools import wraps
from argparse import ArgumentTypeError

from .iter import is_empty
from .stdio import confirm
from .compat.pathlib import Path

def get_args(argparser):
	""" get commandline arguments from std input instead """

	from pprint import pprint

	if len(sys.argv) > 1:
		return argparser.parse_args()

	print("stdin")
	args = []

	for action in argparser._actions:
		pprint(action)

	for k, v in argparser._option_string_actions.items():

		nargs = v.nargs if v.nargs is not None else 1

		if nargs == 0:
			if confirm(str(k)):
				args.append(k)
		else:
			instr = input("{} ({}): ".format(k, nargs)) # separate multiple value by whitespace, quoting supported.
			args.append(k)
			args.append(instr)

	args = shlex.split(" ".join(args))
	pprint(args)
	return argparser.parse_args(args)

def arg_to_path(func):
	# type: (Callable[[Path], Path], ) -> Callable

	@wraps(func)
	def inner(path):
		return func(Path(path))
	return inner

def multiple_of(divisor):
	# type: (int, ) -> Callable[[str], int]

	from builtins import int as builtin_int

	""" This function is called 'int' so that argparse can show a nicer error message
		in case input cannot be cast to int:
		error: argument --multiple: invalid int value: 'a'
	"""
	def int(s):
		# type: (str, ) -> int

		number = builtin_int(s)

		if number % divisor != 0:
			msg = "{0} is not clearly divisible by {1}".format(s, divisor)
			raise ArgumentTypeError(msg)

		return number

	return int

def in_range(start, stop, step=1):
	# type: (int, int, int) -> Callable[[str], int]


	from builtins import int as builtin_int

	def int(s): # see: multiple_of()
		# type: (str, ) -> int

		number = builtin_int(s)

		r = range(start, stop, step)
		if number not in r:
			msg = "{0} is not in {1}".format(s, r)
			raise ArgumentTypeError(msg)

		return number

	return int

def suffix(s):
	# type: (str, ) -> str

	""" Checks if `s` is a valid suffix. """

	if not s.startswith("."):
		msg = "{0} is not a valid suffix. It must start with a dot.".format(s)
		raise ArgumentTypeError(msg)

	return s

@arg_to_path
def existing_path(path):
	# type: (Path, ) -> Path

	""" Checks if a path exists. """

	if not path.exists():
		msg = "{0} does not exist".format(path)
		raise ArgumentTypeError(msg)

	return path

@arg_to_path
def new_path(path):
	# type: (Path, ) -> Path

	""" Checks if a path exists. """

	if path.exists():
		msg = "{0} does not exist".format(path)
		raise ArgumentTypeError(msg)

	return path

@arg_to_path
def is_dir(path):
	# type: (Path, ) -> Path

	"""Checks if a path is an actual directory"""

	if not path.is_dir():
		msg = "{0} is not a directory".format(path)
		raise ArgumentTypeError(msg)

	return path

@arg_to_path
def abs_path(path):
	# type: (Path, ) -> Path

	"""Checks if a path is an actual directory"""

	return path.resolve()

@arg_to_path
def is_file(path):
	# type: (Path, ) -> Path

	"""Checks if a path is an actual file"""

	if not path.is_file():
		msg = "{0} is not a file".format(path)
		raise ArgumentTypeError(msg)

	return path

@arg_to_path
def future_file(path):
	# type: (Path, ) -> Path

	""" Tests if file can be created to catch errors early.
		Checks if directory is writeable and file does not exist yet.
	"""

	if path.parent and not os.access(str(path.parent), os.W_OK):
		msg = "cannot access directory {0}".format(path.parent)
		raise ArgumentTypeError(msg)
	if path.is_file():
		msg = "file {0} already exists".format(path)
		raise ArgumentTypeError(msg)
	return path

@arg_to_path
def empty_dir(dirname):
	# type: (Path, ) -> Path

	""" tests if directory is empty """

	if not is_empty(os.scandir(dirname)):
		msg = "directory {0} is not empty".format(dirname)
		raise ArgumentTypeError(msg)

	return dirname

if __name__ == "__main__":

	from argparse import ArgumentParser

	parser = ArgumentParser()
	parser.add_argument('--str')
	parser.add_argument('--required', action='store_true')
	parser.add_argument('--add', nargs="+")
	print(get_args(parser))

	"""
	parser = ArgumentParser()
	parser.add_argument('--indir', type=is_dir)
	parser.add_argument('--infile', type=is_file)
	parser.add_argument('--outfile', type=future_file)
	parser.add_argument('--outdir', type=empty_dir)
	args = parser.parse_args()
	print(args)
	"""
