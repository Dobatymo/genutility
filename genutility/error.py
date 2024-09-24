from functools import wraps
from typing import Callable, TypeVar
from warnings import warn

from typing_extensions import ParamSpec

T = TypeVar("T")
P = ParamSpec("P")


def deprecated(msg: str, stacklevel: int = 2) -> Callable[[Callable[P, T]], Callable[P, T]]:
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        def inner(*args: P.args, **kwargs: P.kwargs) -> T:
            warn(msg, DeprecationWarning, stacklevel)  # noqa: B028
            print("DeprecationWarning:", msg)
            return func(*args, **kwargs)

        return inner

    return decorator
