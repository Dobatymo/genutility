import logging
import os.path
from datetime import datetime, timedelta
from functools import partial, reduce, wraps
from sys import stdout
from time import sleep
from typing import Any, Callable, Iterable, Iterator, Optional, Sequence, TextIO, TypeVar, Union

from typing_extensions import ParamSpec

from ._func import rename, renameobj  # noqa: F401
from .iter import nonstriter, retrier
from .typing import ExceptionsType

T = TypeVar("T")
U = TypeVar("U")
It = TypeVar("It", bound=Iterable)
P = ParamSpec("P")

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


def compose_two(f: Callable[[Any], Any], g: Callable[[Any], Any]) -> Callable[[Any], Any]:
    """compose_two(f, g) -> lambda x: f(g(x))"""

    return lambda x: f(g(x))


def compose(*functions: Callable[[Any], Any]) -> Callable[[Any], Any]:
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


def call_repeated(num: int) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Function decorator to call decorated function `num` times with the same arguments.
    Returns the results of the last call.
    """

    if num < 1:
        raise ValueError("num must be larger than 0")

    def dec(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        def inner(*args: P.args, **kwargs: P.kwargs) -> T:
            last = None
            for _i in range(num):
                last = func(*args, **kwargs)
            return last

        return inner

    return dec


def print_return_type(func: Callable[P, T], file: TextIO = stdout) -> Callable[P, T]:
    """Wraps function to print the return type after calling."""

    @wraps(func)
    def inner(*args: P.args, **kwargs: P.kwargs) -> T:
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
    exceptions: ExceptionsType = Exception,
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


def default_except(
    exceptions: ExceptionsType, default: T, func: Callable[P, U], *args: P.args, **kwargs: P.kwargs
) -> Union[T, U]:
    """Call `func(*args, **kwargs)` and turn `exceptions` into `default`."""

    try:
        return func(*args, **kwargs)
    except exceptions:
        return default


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

    def __init__(self, reader: Callable[[str], T], writer: Callable[[T, str], None]) -> None:
        self.reader = reader
        self.writer = writer

    def cache(self, path: str) -> Callable[[Callable[P, T]], Callable[P, T]]:
        def dec(func: Callable[P, T]) -> Callable[P, T]:
            @wraps(func)
            def inner(*args: P.args, **kwargs: P.kwargs) -> T:
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
    def __init__(self, delta: timedelta, func: Callable) -> None:
        self.delta = delta
        self.func = func
        self.lastrun: Optional[datetime] = None

    def __call__(self, *args, **kwargs) -> None:
        now = datetime.now()
        if self.lastrun is None or now - self.lastrun > self.delta:
            self.func(*args, **kwargs)
            self.lastrun = now


def applymap(func: Callable[..., T], it: Iterable[tuple]) -> Iterator[T]:
    """Maps `func` over the unpacked `it`."""

    return (func(*args) for args in it)
