import tracemalloc
from typing import Optional

from typing_extensions import Self


class MeasureMemory:
    __slots__ = ("total", "snapshot")

    total: Optional[int]

    def __init__(self) -> None:
        tracemalloc.start()

        self.total = None

    def _comp(self) -> int:
        snapshot_now = tracemalloc.take_snapshot()
        stats = snapshot_now.compare_to(self.snapshot, "lineno")
        return sum(stat.size for stat in stats)

    def __enter__(self) -> Self:
        self.snapshot = tracemalloc.take_snapshot()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
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
