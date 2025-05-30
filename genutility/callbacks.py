from typing import Any, Iterable, Iterator, Optional, Sequence, Type, TypeVar, Union

from typing_extensions import Self, final

T = TypeVar("T")


@final
class _Default:
    pass


class BaseTask:
    def advance(self, delta: float) -> None:
        raise NotImplementedError

    def update(
        self,
        *,
        completed: Union[Optional[float], Type[_Default]] = _Default,
        total: Union[Optional[float], Type[_Default]] = _Default,
        description: Union[Optional[str], Type[_Default]] = _Default,
        **fields: Any,
    ) -> None:
        raise NotImplementedError

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass


class Task(BaseTask):
    def __init__(self, total: Optional[float] = None, description: Optional[str] = None) -> None:
        pass

    def advance(self, delta: float) -> None:
        pass

    def update(
        self,
        *,
        completed: Union[Optional[float], Type[_Default]] = _Default,
        total: Union[Optional[float], Type[_Default]] = _Default,
        description: Union[Optional[str], Type[_Default]] = _Default,
        **fields: Any,
    ):
        pass


class Progress:
    def track(
        self,
        sequence: Union[Iterable[T], Sequence[T]],
        total: Optional[float] = None,
        description: Optional[str] = None,
        **fields: Any,
    ) -> Iterator[T]:
        yield from sequence

    def task(self, total: Optional[float] = None, description: Optional[str] = None, **fields: Any) -> BaseTask:
        return Task(total, description, **fields)

    def set_prolog(self, prolog: Any) -> None:
        pass

    def set_epilog(self, epilog: Any) -> None:
        pass

    def print(self, s: str, end="\n") -> None:
        print(s, end=end)
