from typing import Any, Iterable, Iterator, Optional, Sequence, TypeVar, Union

from tqdm import tqdm

from .callbacks import BaseTask
from .callbacks import Progress as _Progress
from .callbacks import _Default

T = TypeVar("T")


class Task(BaseTask):
    def __init__(self, total: Optional[float] = None, description: Optional[float] = None, **kwargs: Any) -> None:
        self.pbar = tqdm(desc=description, total=total, **kwargs)

    def __enter__(self) -> BaseTask:
        return self

    def __exit__(self, *args):
        self.pbar.close()

    def advance(self, delta: float) -> None:
        self.pbar.update(n=delta)

    def update(
        self,
        *,
        completed: Optional[float] = _Default,
        total: Optional[float] = _Default,
        description: Optional[str] = _Default,
        **kwargs: Any
    ) -> None:
        if completed is not _Default:
            self.pbar.n = completed
        if total is not _Default:
            self.pbar.total = total
        if description is not _Default:
            self.pbar.set_description(description)


class Progress(_Progress):
    def track(
        self,
        sequence: Union[Iterable[T], Sequence[T]],
        total: Optional[float] = None,
        description: Optional[str] = None,
        **kwargs: Any
    ) -> Iterator[T]:
        return tqdm(sequence, description, total, **kwargs)

    def task(self, total: Optional[float] = None, description: Optional[str] = None, **kwargs: Any):
        return Task(total, description, **kwargs)

    def set_prolog(self, prolog: str) -> None:
        raise NotImplementedError

    def set_epilog(self, epilog: str) -> None:
        raise NotImplementedError

    def print(self, s: str, end="\n") -> None:
        tqdm.write(s, end=end)
