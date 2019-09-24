from __future__ import absolute_import, division, print_function, unicode_literals

from builtins import input, str
from future.utils import PY3

import sys, logging
from time import sleep

try:
	from shutil import get_terminal_size
	_terminal_width = get_terminal_size((80, 30)).columns
except ImportError: # < Python 3.3
	_terminal_width = 80

def print_line(char="-", length=_terminal_width, file=None, flush=False):
	# type: (str, int, IO, bool) -> None
	""" file=None, defaults to sys.stdout in print(). print() handles sys.stdout==None fine. """

	print(char*length, end="", file=file, flush=flush)

def safe_input(s, block=10):
	""" makes sure ctrl-c on input() only raises KeyboardInterrupt and not EOFError+KeyboardInterrupt.
		Waits at most `block` seconds to be sure.
	"""

	try:
		return input(s)
	except EOFError:
		sleep(block) # can be interrupted by KeyboardInterrupt

def info_print(msg=None, args=tuple(), exception=None):
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
		# type: (str, filelike, filelike) -> str

		print(s, file=file_out, end="")
		file_out.flush()
		return sys.stdin.readline().rstrip("\n")

else:
	def input_ex(s, file_out=sys.stdout, file_in=sys.stdin):
		# type: (str, filelike, filelike) -> str

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
	if yesno:
		s = input_type(msg+" (yes, no): ", predicate=lambda x: x.strip().lower() in {"yes", "no"})
		return s.strip().lower() == "yes"
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
