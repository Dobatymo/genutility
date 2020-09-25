from __future__ import absolute_import, division, print_function, unicode_literals

from builtins import input, str
from future.utils import PY3

import logging
import sys
from time import sleep
from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from typing import IO, Any, Optional

try:
	from shutil import get_terminal_size
	_terminal_width = get_terminal_size((80, 30)).columns
except ImportError: # < Python 3.3
	_terminal_width = 80

def print_line(char="-", length=_terminal_width, file=None, flush=False):
	# type: (str, int, IO, bool) -> None
	""" file=None, defaults to sys.stdout in print(). print() handles sys.stdout==None fine. """

	print(char*length, end="", file=file, flush=flush)

class PrintOnError(object):

	""" A context manager which can be used to output data
		before an exception is printed by the python runtime.
	"""

	def __init__(self, *args, **kwargs):
		# type: (*Any, **Any) -> None

		""" All arguments are passed to the `print` function. """

		self.args = args
		self.kwargs = kwargs

	def __enter__(self):
		# type: () -> PrintOnError

		return self

	def __exit__(self, exc_type, exc_value, traceback):
		if exc_type:
			print(*self.args, **self.kwargs)

def safe_input(s, block=10):
	# type: (str, int) -> str

	""" Makes sure ctrl-c on input() only raises KeyboardInterrupt and not EOFError+KeyboardInterrupt.
		Waits at most `block` seconds to be sure.
	"""

	try:
		return input(s)
	except EOFError:
		sleep(block) # can be interrupted by KeyboardInterrupt

def info_print(msg=None, args=tuple(), exception=None):
	# type: (Optional[str], tuple, Exception) -> None

	# not (msg or exception) this doesn't do anything

	if exception and msg:
		logging.exception(msg % args, exc_info=exception)
		#logging.exception(msg, *args, exc_info=exception) this fails for some weird reason
	else:
		if exception:
			logging.exception("Unhandled exception", exc_info=exception)
		if msg:
			print(msg % args)

if PY3:
	def input_ex(s, file_out=sys.stdout, file_in=sys.stdin):
		# type: (str, IO, IO) -> str

		print(s, file=file_out, end="")
		file_out.flush()
		return sys.stdin.readline().rstrip("\n")

else:
	def input_ex(s, file_out=sys.stdout, file_in=sys.stdin):
		# type: (str, IO, IO) -> str

		print(s.encode(file_out.encoding, errors="replace"), file=file_out, end=b"")
		return sys.stdin.readline().decode(file_in.encoding).rstrip("\n")

# was: raw_input_ex
def input_type(s, type=None, predicate=None, errormsg=None, exception=Exception, file=sys.stdout):
	while True:
		ret = input_ex(s, file_out=file)
		if predicate and not predicate(ret):
			if errormsg:
				print(errormsg % (ret,))
			continue
		if type:
			try:
				return type(ret)
			except exception:
				if errormsg:
					print(errormsg % (ret,))
				continue
		return ret

def confirm(msg, yesno=True):
	# type: (str, bool) -> bool

	if yesno:
		s = input_type(msg+" (yes, no): ", predicate=lambda x: x.strip().lower() in {"yes", "y", "n", "no"})
		return s.strip().lower() in {"yes", "y"}
	else:
		return input_type(msg+" (anything, nothing): ", type=bool) # bool cannot throw if given string I think...

def waitquit(msg=None, args=tuple(), exception=None): # fixme: ferutility.printing breaks this
	info_print(msg, args, exception)
	input("Press enter to exit...")
	sys.exit(msg or exception)

def waitcontinue(msg=None, args=tuple(), exception=None):
	info_print(msg, args, exception)
	input("Press enter to continue...")

def errorquit(msg=None, args=tuple(), exception=None):
	info_print(msg, args, exception)
	sys.exit(msg or exception)
