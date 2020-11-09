from __future__ import absolute_import, division, print_function, unicode_literals

from builtins import input, range

import os
import os.path
import shlex
import sys
from argparse import ArgumentTypeError
from functools import wraps
from typing import TYPE_CHECKING

from .compat.os import makedirs
from .compat.pathlib import Path
from .iter import is_empty
from .stdio import confirm

if TYPE_CHECKING:
	from typing import Callable

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
			instr = input("{} ({}): ".format(k, nargs))  # separate multiple value by whitespace, quoting supported.
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

	def int(s):  # see: multiple_of()
		# type: (str, ) -> int

		number = builtin_int(s)

		r = range(start, stop, step)
		if number not in r:
			msg = "{0} is not in {1}".format(s, r)
			raise ArgumentTypeError(msg)

		return number

	return int

def between(start, stop):
	# type: (float, float) -> Callable[[str], float]

	from builtins import float as builtin_float

	def float(s):
		# type: (str, ) -> float

		number = builtin_float(s)

		if not (start <= number < stop):
			msg = "{0} is not in between {1} and {2}".format(s, start, stop)
			raise ArgumentTypeError(msg)

		return number

	return float

def suffix(s):
	# type: (str, ) -> str

	""" Checks if `s` is a valid suffix. """

	if not s.startswith("."):
		msg = "{0} is not a valid suffix. It must start with a dot.".format(s)
		raise ArgumentTypeError(msg)

	return s

def lowercase(s):
	# type: (str, ) -> str

	""" Converts argument to lowercase. """

	return s.lower()

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
		msg = "{0} already exists".format(path)
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
def out_dir(path):
	# type: (Path, ) -> Path

	""" Tests if `path` is a directory. If not it tries to create one.
	"""

	if not path.is_dir():
		try:
			makedirs(path)
		except OSError:
			msg = "Error: '{}' is not a valid directory.".format(path)
			raise ArgumentTypeError(msg)

	return path

@arg_to_path
def empty_dir(dirname):
	# type: (Path, ) -> Path

	""" tests if directory is empty """

	with os.scandir(dirname) as it:
		if not is_empty(it):
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
