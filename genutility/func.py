from __future__ import generator_stop

import logging
import os.path
from datetime import datetime, timedelta
from functools import partial, reduce, wraps
from sys import stdout
from time import sleep
from typing import Any, Callable, Iterable, Iterator, Optional, Sequence, TextIO, Tuple, Type, TypeVar, Union

from ._func import rename, renameobj  # noqa: F401
from .iter import nonstriter, retrier

T = TypeVar("T")
U = TypeVar("U")
It = TypeVar("It", bound=Iterable)

logger = logging.getLogger(__name__)


class NotRetried(RuntimeError):
    pass


def identity(x: T) -> T:

    """Identity function."""

    return x


def nop() -> None:

    """Function which does absolutely nothing (aka pass, noop)."""

    pass


def partial_decorator(*args: Any, **kwargs: Any) -> Callable:

    """Same as `functools.partial` but applied as a decorator."""

    def decorator(func):
        return partial(func, *args, **kwargs)

    return decorator


def compose_two(f, g):
    # type: (Callable[[Any], Any], Callable[[Any], Any]) -> Callable[[Any], Any]

    """compose_two(f, g) -> lambda x: f(g(x))"""

    return lambda x: f(g(x))


def compose(*functions):
    # type: (*Callable[[Any], Any]) -> Callable[[Any], Any]

    """compose(f, g, h) -> lambda x: f(g(h(x))).
    see: Function composition
    """

    return reduce(compose_two, functions, identity)


def apply(f: Callable[[T], U], x: T) -> U:  # *args, **kwargs

    """Same as `f(x)`."""

    return f(x)


def zipmap(funcs: Iterable[Callable[[T], U]], vals: Iterable[T]) -> Iterator[U]:

    """Applies a list of functions to a list of values."""

    return map(apply, funcs, vals)


def multiapply(funcs: Iterable[Callable], elm: Any) -> Any:

    """Applies functions `funcs` to element `elm` iteratively."""

    for func in funcs:
        elm = func(elm)

    return elm


def multimap(funcs: Sequence[Callable], it: Iterable) -> Iterator:

    """Applies functions `funcs` to each element of `it` iteratively."""

    for i in it:
        yield multiapply(funcs, i)


def deepmap(func: Callable, *iterables: Iterable) -> Iterator:

    """Simlar to `map`, but it maps recursively over sequences of sequnces.
    Returns a generator of generators.
    To output plain objects use `recmap` instead.

    Example:
    deepmap(lambda x: x*2, [1, [2, 3]]) -> (2, (4, 6))
    """

    if not iterables:
        raise ValueError("iterables must have a least one element")

    for args in zip(*iterables):
        try:
            its = tuple(map(nonstriter, args))
        except TypeError:
            yield func(*args)
        else:
            yield deepmap(func, *its)


def outermap(func: Callable[[T], U], iterable: It) -> Union[It, U]:

    """Examples:
    outermap(list, (1, (2, 3))) -> [1, [2, 3]]
    outermap(sum, (1, (2, 3)) -> 6
    """

    try:
        it = nonstriter(iterable)
    except TypeError:
        return iterable
    else:
        return func(outermap(func, i) for i in it)


def recmap(func: Callable, iterable: Iterable[Any]) -> list:

    """Simlar to `map`, but it maps recursively over sequences of sequnces and puts the result into a list of lists.
    To return a generator of generators use `deepmap` instead.

    Example:
    recmap(lambda x: x*2, [1, [2, 3]]) -> [2, [4, 6]]
    """

    return outermap(list, deepmap(func, iterable))


def call_repeated(num: int) -> Callable[[Callable], Callable]:

    """Function decorator to call decorated function `num` times with the same arguments.
    Returns the results of the last call.
    """

    if num < 1:
        raise ValueError("num must be larger than 0")

    def dec(func):
        @wraps(func)
        def inner(*args, **kwargs):
            last = None
            for i in range(num):
                last = func(*args, **kwargs)
            return last

        return inner

    return dec


def print_return_type(func: Callable, file: TextIO = stdout) -> Callable:

    """Wraps function to print the return type after calling."""

    @wraps(func)
    def inner(*args, **kwargs):
        ret = func(*args, **kwargs)
        print(type(ret), file=file)
        return ret

    return inner


def get_callable_name(func: Callable) -> str:
    """Unwraps common function wrappers and tries to return the full qualified function name."""

    if isinstance(func, partial):
        func = func.func

    return getattr(func, "__qualname__", repr(func))


def retry(
    func: Callable[[], T],
    waittime: float,
    exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = (Exception,),
    attempts: int = -1,
    multiplier: float = 1,
    jitter: float = 0,
    max_wait: Optional[float] = None,
    jitter_dist: str = "uniform",
    waitfunc: Callable[[float], Any] = sleep,
) -> T:

    """Retry function `func` multiple times in case of raised `exceptions`.
    See `genutility.iter.retrier()` for the remaining arguments.
    Reraises the last exception in case the function call doesn't succeed after retrying.
    """

    last_exception: Optional[Exception] = None
    for i in retrier(waittime, attempts, multiplier, jitter, max_wait, jitter_dist, waitfunc):
        try:
            return func()
        except exceptions as e:
            name = get_callable_name(func)
            logger.info("Attempt %s (%s) failed: %s", i + 1, name, e)
            last_exception = e

    if last_exception:
        raise last_exception  # pylint: disable=raising-bad-type
    else:
        raise NotRetried


class CustomCache:

    """Class to build decorator cache function using custom reader and writer functions.
    The cache method ignores all arguments of the decorated function.

    Example:
    ```
    cc = CustomCache(read_pickle, write_pickle)

    @cc.cache("func-cache.p")
    # arg is ignored, so the cache will return the result of the argument which was supplied
    # when the cache file was created.
    def func(arg):
            return arg
    ```
    a = func(1) # cache created, a == 1
    b = func(2) # cache loaded, b == 1
    """

    def __init__(self, reader, writer):
        # type: (Callable, Callable) -> None

        self.reader = reader
        self.writer = writer

    def cache(self, path):
        # type: (str, ) -> Callable

        def dec(func):
            # type: (Callable, ) -> Callable

            @wraps(func)
            def inner(*args, **kwargs):
                # type: (*Any, **Any) -> Any

                if os.path.exists(path):
                    logger.debug("Loading object from cache %s", path)
                    return self.reader(path)
                else:
                    logger.debug("Saving obect to cache %s", path)
                    result = func(*args, **kwargs)
                    self.writer(result, path)
                    return result

            return inner

        return dec


class RunScheduled:
    def __init__(self, delta: timedelta, func: Callable):
        self.delta = delta
        self.func = func
        self.lastrun: Optional[datetime] = None

    def __call__(self, *args, **kwargs):
        now = datetime.now()
        if self.lastrun is None or now - self.lastrun > self.delta:
            self.func(*args, **kwargs)
            self.lastrun = now


def applymap(func, it):
    # type: (Callable[..., T], Iterable[tuple]) -> Iterator[T]

    """Maps `func` over the unpacked `it`."""

    return (func(*args) for args in it)
