from __future__ import absolute_import, division, print_function, unicode_literals

from collections import defaultdict
from datetime import timedelta
from time import sleep
from typing import TYPE_CHECKING

try:
	from time import monotonic  # Python 3.5+
except ImportError:
	from time import clock as monotonic

if TYPE_CHECKING:
	from typing import Any, Callable, Hashable, Iterator, Optional, Tuple, TypeVar, Union
	T = TypeVar("T")

def iter_timer(it):
	# type: (Iterator[T], ) -> Iterator[Tuple[T, float]]
	try:
		while True:
			start = monotonic()
			res = next(it)
			delta = monotonic()-start
			yield res, delta
	except StopIteration:
		pass

class TakeAtleast(object):

	def __init__(self, delta, wait_on_error=False):
		# type: (Union[float, timedelta], ) -> None

		if isinstance(delta, timedelta):
			self.delta = delta.total_seconds()
		else:
			self.delta = float(delta)

		self.wait_on_error = wait_on_error

	def __enter__(self):
		self.now = monotonic()

	def __exit__(self, exc_type, exc_value, traceback):

		if exc_type is None or self.wait_on_error:
			elapsed = monotonic() - self.now
			if elapsed < self.delta:
				sleep(self.delta - elapsed)

class DeltaTime(object):

	__slots__ = ("start", "end")

	def __init__(self):
		# type: () -> None

		self.start = None # type: Optional[float]
		self.end = monotonic()

	def __iter__(self):
		# type: () -> DeltaTime

		return self

	def __next__(self):
		# type: () -> float

		self.start, self.end = self.end, monotonic()
		return self.end - self.start

	def get(self):
		# type: () -> float

		return monotonic() - self.end

	def reset(self):
		# type: () -> None

		self.end = monotonic()

	def get_reset(self):
		# type: () -> float

		self.start, self.end = self.end, monotonic()
		return self.end - self.start

class PrintStatementTime(object):

	__slots__ = ("tpl", "start")

	def __init__(self, tpl=None):
		# type: (Optional[str], ) -> None
		if tpl is None:
			self.tpl = "Execution took {delta}s"
		else:
			self.tpl = tpl

	def __enter__(self):
		self.start = monotonic()
		return self

	def __exit__(self, exc_type, exc_value, traceback):
		end = monotonic()
		delta = end - self.start
		msg = self.tpl.format(start=self.start, end=end, delta=delta)
		if exc_type:
			print(msg + " (interrupted)")
		else:
			print(msg)

class MeasureTime(object):

	__slots__ = ("delta", "start")

	def __init__(self):
		# type: () -> None
		self.delta = None

	def __enter__(self):
		self.start = monotonic()
		return self

	def __exit__(self, type, value, traceback):
		self.delta = monotonic() - self.start

	def get(self):
		# type: () -> float
		if self.delta:
			return self.delta
		else:
			return monotonic() - self.start

class TimeIt(object):

	def __init__(self):
		self.results = defaultdict(list)
		self.starts = dict()

	def __call__(self, key, func, *args, **kwargs):
		# type: (Hashable, Callable, *Any, **Any) -> Any

		with MeasureTime() as t:
			ret = func(*args, **kwargs)
		self.results[key].append(t.get())
		return ret

	def start(self, key):
		# type: (Hashable, ) -> None
		self.starts[key] = DeltaTime()

	def stop(self, key):
		# type: (Hashable, ) -> None
		self.results[key].append(self.starts[key].get())

	def min(self, key):
		# type: (Hashable, ) -> float
		return min(self.results[key])

	def length(self, key):
		# type: (Hashable, ) -> int
		return len(self.results[key])
