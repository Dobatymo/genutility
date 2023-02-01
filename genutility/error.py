from functools import wraps
from typing import Callable
from warnings import warn


def deprecated(msg: str, stacklevel: int = 2) -> Callable[[Callable], Callable]:
    def decorator(func):
        @wraps(func)
        def inner(*args, **kwargs):
            warn(msg, DeprecationWarning, stacklevel)
            print("DeprecationWarning:", msg)
            return func(*args, **kwargs)

        return inner

    return decorator
