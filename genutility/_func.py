from typing import Callable, Optional


def rename(func_name: str, func_qualname: Optional[str] = None) -> Callable:
    def decorator(func: Callable):
        func.__name__ = func_name
        func.__qualname__ = func_qualname or func_name
        return func

    return decorator


def renameobj(name: str, obj) -> None:
    obj.__class__ = type(name, (obj.__class__,), {})
