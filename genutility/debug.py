from __future__ import generator_stop

import logging
from collections import defaultdict
from functools import wraps
from typing import Any, Callable, Iterable, Optional


def printr(*objs: Any, end: str = "\n", depth: int = 0) -> None:

    for i, obj in enumerate(objs, 1):

        if isinstance(obj, str):
            print(obj, end="")
        elif isinstance(obj, dict):
            print("{", end="")
            for j, (k, v) in enumerate(obj.items(), 1):
                printr(k, end=end, depth=depth + 1)
                print(": ", end="")
                printr(v, end=end, depth=depth + 1)
                if j != len(obj):
                    print(", ", end="")
            print("}", end="")
        else:
            try:
                print("(", end="")
                for j, item in enumerate(obj, 1):
                    printr(item, end=end, depth=depth + 1)
                    if j != len(obj):
                        print(", ", end="")
                print(")", end="")
            except TypeError:
                print(obj, end="")

        if i != len(objs):
            print(" ", end="")

    if depth == 0:
        print(end=end)


def _to_union(types: Iterable[str]) -> str:

    types = list(set(types))

    if not types:
        return ""
    elif len(types) == 1:
        return types[0]
    elif len(types) > 1:
        return "Union[" + ", ".join(types) + "]"

    assert False


def _type_str(obj: Any) -> str:

    return type(obj).__name__


def rec_repr(obj: Any) -> str:

    if isinstance(obj, defaultdict):
        return _type_str(obj) + "[" + rec_repr(obj.default_factory) + "]"
    elif isinstance(obj, list):
        return "List[" + _to_union(map(rec_repr, obj)) + "]"
    elif isinstance(obj, set):
        return "Set[" + _to_union(map(rec_repr, obj)) + "]"
    else:
        return _type_str(obj)


def _arg_str(arg: Any, maxlen: Optional[int] = None, app: str = "...", repr_args: bool = True) -> str:

    if repr_args:
        arg = repr(arg)

    assert isinstance(arg, str)

    if maxlen:
        if len(arg) <= maxlen + len(app):
            return arg
        else:
            return arg[:maxlen] + app
    else:
        return arg


def _kwarg_str(key: str, value: Any, maxlen: Optional[int] = None, app: str = "...", repr_args: bool = True) -> str:

    return key + "=" + _arg_str(value, maxlen, app, repr_args)


def args_str(args: tuple, kwargs: dict, maxlen: Optional[int] = 20, app: str = "...", repr_args: bool = True) -> str:

    """Creates printable string from function arguments.
    If the string needs to be truncated to fit `maxlen`, `app` will be appended.
    The length of `app` is not included in `maxlen`.
    If the original string is shorter or equal `maxlen + len(app)`,
    it will be returned unmodified.
    """

    args = ", ".join(_arg_str(arg, maxlen, app, repr_args) for arg in args)
    kwargs = ", ".join(_kwarg_str(k, v, maxlen, app, repr_args) for k, v in kwargs.items())

    if args:
        if kwargs:
            return args + ", " + kwargs
        else:
            return args
    else:
        if kwargs:
            return kwargs
        else:
            return ""


def log_call(s: str) -> Callable:

    """Decorator to log function calls using template string `s`.
    Available format fields are: 'name', 'args' and 'kwargs'.
    """

    def dec(func: Callable) -> Callable:
        def inner(*args, **kwargs):
            logging.debug(s.format(name=func.__name__, args=args, kwargs=kwargs))
            return func(*args, **kwargs)

        return inner

    return dec


def log_wrap_call(func: Callable) -> Callable:

    """Decorator which logs all calls to `func` with all arguments."""

    @wraps(func)
    def inner(*args, **kwargs):
        logging.debug("START %s(%s)", func.__name__, args_str(args, kwargs))

        try:
            ret = func(*args, **kwargs)
        except BaseException:
            logging.exception("RAISED %s(%s)", func.__name__, args_str(args, kwargs))
            raise

        logging.debug("END %s(%s)", func.__name__, args_str(args, kwargs))
        return ret

    return inner


def log_methodcall(func: Callable) -> Callable:

    """Decorator to log method calls with arguments."""

    @wraps(func)
    def inner(self, *args, **kwargs):
        classname = self.__class__.__name__
        # classname = type(self).__name__ ?
        logging.debug("%s.%s(%s)", classname, func.__name__, args_str(args, kwargs))
        return func(self, *args, **kwargs)

    return inner


def log_methodcall_result(func: Callable) -> Callable:

    """Decorator to log method calls with arguments and results."""

    @wraps(func)
    def inner(self, *args, **kwargs):
        classname = self.__class__.__name__
        # classname = type(self).__name__ ?
        logging.debug("%s.%s(%s)", classname, func.__name__, args_str(args, kwargs))
        res = func(self, *args, **kwargs)
        logging.debug("%s.%s => %s", classname, func.__name__, res)
        return res

    return inner
