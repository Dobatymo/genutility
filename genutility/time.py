from __future__ import generator_stop

from collections import defaultdict
from datetime import timedelta
from time import monotonic, sleep
from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from typing import Any, Callable, DefaultDict, Dict, Hashable, Iterator, List, Optional, Tuple, TypeVar, Union
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

	__slots__ = ("delta", "wait_on_error", "now")

	def __init__(self, delta, wait_on_error=False):
		# type: (Union[float, timedelta], bool) -> None

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

		self.delta = None # type: Optional[float]

	def __enter__(self):
		# type: () -> MeasureTime

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
		# type: () -> None

		self.results = defaultdict(list) # type: DefaultDict[Hashable, List[float]]
		self.starts = dict() # type: Dict[Hashable, DeltaTime]

	def __call__(self, key, func, *args, **kwargs):
		# type: (Hashable, Callable[..., T], *Any, **Any) -> T

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
