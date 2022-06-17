from __future__ import generator_stop

import tracemalloc
from typing import Optional


class MeasureMemory:

    __slots__ = ("total", "snapshot")

    def __init__(self) -> None:

        tracemalloc.start()

        self.total: Optional[int] = None

    def _comp(self) -> int:

        snapshot_now = tracemalloc.take_snapshot()
        stats = snapshot_now.compare_to(self.snapshot, "lineno")
        return sum(stat.size for stat in stats)

    def __enter__(self) -> "MeasureMemory":

        self.snapshot = tracemalloc.take_snapshot()
        return self

    def __exit__(self, type, value, traceback):
        self.total = self._comp()

    def get(self) -> int:

        if self.total:
            return self.total
        else:
            return self._comp()

    def print(self, name: str) -> None:

        if self.total:
            total = self.total
        else:
            total = self._comp()

        print(f"{name} uses {total / 1024 / 1024:.3f} MiB of memory")
