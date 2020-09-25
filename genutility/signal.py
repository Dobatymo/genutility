from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import signal
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from types import FrameType
	from typing import Any, Callable, Iterable, Optional, TypeVar, Union
	if sys.version_info >= (3, 5):
		from signal import Signals  # pylint: disable=no-name-in-module
	else:
		Signals = int

	T = TypeVar("T")

logger = logging.getLogger(__name__)

class HandleKeyboardInterrupt(object):

	""" Context manager to handle ctrl-c (keyboard interrupts)
	
		with HandleKeyboardInterrupt():
			do_a()
			do_b()

		Any KeyboardInterrupt received within the context manager will be caught and possibly
		re-raised at the end of the block. It can be used to make sure that sensitive code is not
		carelessly interrupted in the middle of execution by the user. The process could still be
		kill though, so this method should only be used as a convenience function, not to implement
		atomic transactions.

		https://stackoverflow.com/questions/842557/how-to-prevent-a-block-of-code-from-being-interrupted-by-keyboardinterrupt-in-py#comment81343976_21919644
		"this code may call third-party exception handlers in threads other than the main thread, which CPython never does"
		so be careful with threads
	"""

	def __init__(self, raise_after=True, delay=-1):
		# type: (bool, int) -> None

		""" If `raise_after` is True, the KeyboardInterrupt will be re-raised when leaving the context.
			`delay` specifies the maximum number of times the signal is caught.
		"""

		self.init_raise_after = raise_after
		self.init_delay = delay

	def __enter__(self):
		# type: () -> None

		self.raise_after = self.init_raise_after # pylint: disable=attribute-defined-outside-init
		self.delay = self.init_delay # pylint: disable=attribute-defined-outside-init
		self.signal_received = None # type: Optional[tuple]
		self.old_handler = signal.signal(signal.SIGINT, self.handler) # type: ignore # cast to Callable[[Signals, FrameType], None]

	def handler(self, sig, frame):
		# type: (Signals, FrameType) -> None

		if self.delay == 0:
			self.raise_after = False
			self.old_handler(sig, frame) # type: ignore # see cast above
		else:
			self.delay -= 1
			self.signal_received = (sig, frame)
			logger.debug("SIGINT received. Delaying KeyboardInterrupt.")

	def __exit__(self, type, value, traceback):
		# should this show a warning for 'IOError: [Errno 4] Interrupted function call' on python 2.7?

		signal.signal(signal.SIGINT, self.old_handler)
		if self.signal_received and self.raise_after:
			self.old_handler(*self.signal_received)

def safe_for_loop(it, body_func, else_func=None):
	# type: (Iterable[T], Callable[[T], bool], Callable[[], Any]) -> None

	""" This function makes sure that `body_func(element)` is called each time an element is retrieved from the
		iterable `it`, even if a `KeyboardInterrupt` is signaled in-between.
		After `body_func` is called, the KeyboardInterrupt will be re-raised and can be caught in
		calling function. `body_func` can optionally return `True` to exit the loop early.
		If the loop finishes, `else_func` will be called if provided.
	"""

	it = iter(it)
	finished = False
	Uninterrupted = HandleKeyboardInterrupt(True)
	while True:
		with Uninterrupted:
			try:
				chunk = next(it)
			except StopIteration:
				finished = True
				break
			if body_func(chunk):
				break
	if finished and else_func: # no break
		with Uninterrupted:
			else_func()
