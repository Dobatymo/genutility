from __future__ import generator_stop

import tracemalloc
from typing import Optional


class MeasureMemory(object):

	__slots__ = ("total", "snapshot")

	def __init__(self):
		# type: () -> None

		tracemalloc.start()

		self.total = None # type: Optional[int]

	def _comp(self):
		# type: () -> int

		snapshot_now = tracemalloc.take_snapshot()
		stats = snapshot_now.compare_to(self.snapshot, "lineno")
		return sum(stat.size for stat in stats)

	def __enter__(self):
		# type: () -> MeasureMemory

		self.snapshot = tracemalloc.take_snapshot()
		return self

	def __exit__(self, type, value, traceback):
		self.total = self._comp()

	def get(self):
		# type: () -> int

		if self.total:
			return self.total
		else:
			return self._comp()

	def print(self, name):
		# type: (str, ) -> None

		if self.total:
			total = self.total
		else:
			total = self._comp()

		print("{} uses {:.3f} MiB of memory".format(name, total / 1024 / 1024))
