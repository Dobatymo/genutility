from typing import Any, Iterable, Iterator, Optional, Sequence, TypeVar, Union

T = TypeVar("T")


class _Default:
    pass


class BaseTask:
    def advance(self, delta: float) -> None:
        raise NotImplementedError

    def update(
        self,
        *,
        completed: Optional[float] = _Default,
        total: Optional[float] = _Default,
        description: Optional[str] = _Default,
        **fields: Any
    ) -> None:
        raise NotImplementedError

    def __enter__(self) -> "BaseTask":
        return self

    def __exit__(self, *args):
        pass


class Task(BaseTask):
    def __init__(self, total: Optional[float] = None, description: Optional[str] = None) -> None:
        pass

    def advance(self, delta: float) -> None:
        pass

    def update(
        self,
        *,
        completed: Optional[float] = _Default,
        total: Optional[float] = _Default,
        description: Optional[str] = _Default,
        **fields: Any
    ):
        pass


class Progress:
    def track(
        self,
        sequence: Union[Iterable[T], Sequence[T]],
        total: Optional[float] = None,
        description: Optional[str] = None,
        **fields: Any
    ) -> Iterator[T]:
        return sequence

    def task(self, total: Optional[float] = None, description: Optional[str] = None, **fields: Any):
        return Task(total, description, **fields)

    def set_prolog(self, prolog: Any) -> None:
        pass

    def set_epilog(self, epilog: Any) -> None:
        pass

    def print(self, s: str, end="\n") -> None:
        print(s, end=end)
