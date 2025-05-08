from typing import Any, Iterable, Iterator, Optional, Sequence, Type, TypeVar, Union

from typing_extensions import Self

from tqdm import tqdm

from .callbacks import BaseTask
from .callbacks import Progress as _Progress
from .callbacks import _Default

T = TypeVar("T")


class Task(BaseTask):
    def __init__(self, total: Optional[float] = None, description: Optional[str] = None, **kwargs: Any) -> None:
        self.pbar = tqdm(desc=description, total=total, **kwargs)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args):
        self.pbar.close()

    def advance(self, delta: float) -> None:
        self.pbar.update(n=delta)

    def update(
        self,
        *,
        completed: Union[Optional[float], Type[_Default]] = _Default,
        total: Union[Optional[float], Type[_Default]] = _Default,
        description: Union[Optional[str], Type[_Default]] = _Default,
        **kwargs: Any,
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
        **kwargs: Any,
    ) -> Iterator[T]:
        yield from tqdm(sequence, description, total, **kwargs)

    def task(self, total: Optional[float] = None, description: Optional[str] = None, **kwargs: Any) -> BaseTask:
        return Task(total, description, **kwargs)

    def set_prolog(self, prolog: str) -> None:
        raise NotImplementedError

    def set_epilog(self, epilog: str) -> None:
        raise NotImplementedError

    def print(self, s: str, end="\n") -> None:
        tqdm.write(s, end=end)
