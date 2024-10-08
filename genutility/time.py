from collections import defaultdict
from datetime import timedelta
from time import perf_counter, sleep
from typing import Callable, DefaultDict, Dict, Hashable, Iterator, List, Optional, Tuple, TypeVar, Union

from typing_extensions import ParamSpec, Self

T = TypeVar("T")
P = ParamSpec("P")


def iter_timer(it: Iterator[T]) -> Iterator[Tuple[T, float]]:
    try:
        while True:
            start = perf_counter()
            res = next(it)
            delta = perf_counter() - start
            yield res, delta
    except StopIteration:
        pass


class TakeAtleast:
    __slots__ = ("delta", "wait_on_error", "now")
    delta: float
    wait_on_error: bool
    now: Optional[float]

    def __init__(self, delta: Union[float, timedelta], wait_on_error: bool = False) -> None:
        """Uses `time.perf_counter` and `os.sleep` to make sure the execution of the code under context manager
        took at least `delta` time. If the code executed faster it will simply sleep afterwards.
        If `wait_on_error` is False and an exception is thrown, it won't sleep.
        """

        if isinstance(delta, timedelta):
            self.delta = delta.total_seconds()
        else:
            self.delta = float(delta)

        self.wait_on_error = wait_on_error
        self.now = None

    def __enter__(self) -> Self:
        self.now = perf_counter()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> Optional[bool]:
        if exc_type is None or self.wait_on_error:
            elapsed = perf_counter() - self.now
            if elapsed < self.delta:
                sleep(self.delta - elapsed)


class DeltaTime:
    __slots__ = ("start", "end")
    start: Optional[float]
    end: float

    def __init__(self) -> None:
        self.start = None
        self.end = perf_counter()

    def __iter__(self) -> Self:
        return self

    def __next__(self) -> float:
        self.start, self.end = self.end, perf_counter()
        return self.end - self.start

    def get(self) -> float:
        return perf_counter() - self.end

    def reset(self) -> None:
        self.end = perf_counter()

    def get_reset(self) -> float:
        self.start, self.end = self.end, perf_counter()
        return self.end - self.start


class PrintStatementTime:
    __slots__ = ("tpl", "start", "delta", "interrupted")
    tpl: str
    start: Optional[float]
    delta: Optional[float]
    interrupted: Optional[bool]

    def __init__(self, tpl: Optional[str] = None) -> None:
        """Times the execution of the code under the context manager and print it afterwards.
        `tpl` is a format string with one field `delta` to include time in seconds.
        The default is `"Execution took {delta}s"`.
        """

        if tpl is None:
            self.tpl = "Execution took {delta}s"
        else:
            self.tpl = tpl
        self.start = None
        self.delta = None
        self.interrupted = None

    def __enter__(self) -> Self:
        self.start = perf_counter()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> Optional[bool]:
        self.delta = perf_counter() - self.start
        msg = self.tpl.format(delta=self.delta)
        if exc_type:
            self.interrupted = True
            print(msg + " (interrupted)")
        else:
            self.interrupted = False
            print(msg)


class MeasureTime:
    __slots__ = ("delta", "start", "interrupted")
    delta: Optional[float]
    start: Optional[float]
    interrupted: Optional[bool]

    def __init__(self) -> None:
        self.delta = None
        self.start = None
        self.interrupted = None

    def __enter__(self) -> Self:
        self.start = perf_counter()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> Optional[bool]:
        self.delta = perf_counter() - self.start
        if exc_type:
            self.interrupted = True
        else:
            self.interrupted = False

    def get(self) -> float:
        if self.start is None:
            raise RuntimeError("Context not entered")

        if self.delta is None:
            return perf_counter() - self.start

        return self.delta


class TimeIt:
    def __init__(self) -> None:
        self.results: DefaultDict[Hashable, List[float]] = defaultdict(list)
        self.starts: Dict[Hashable, DeltaTime] = {}

    def __call__(self, key: Hashable, func: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
        with MeasureTime() as t:
            ret = func(*args, **kwargs)
        self.results[key].append(t.get())
        return ret

    def start(self, key: Hashable) -> None:
        self.starts[key] = DeltaTime()

    def stop(self, key: Hashable) -> None:
        self.results[key].append(self.starts[key].get())

    def min(self, key: Hashable) -> float:
        return min(self.results[key])

    def length(self, key: Hashable) -> int:
        return len(self.results[key])
