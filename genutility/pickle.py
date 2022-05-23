from __future__ import generator_stop

import importlib
import logging
import os.path
import pickle  # nosec
from datetime import timedelta
from functools import wraps
from os import PathLike, fspath
from pathlib import Path
from pickle import HIGHEST_PROTOCOL  # nosec
from typing import Any, Callable, Iterable, Iterator, Optional, Tuple, Union

from .atomic import sopen
from .datetime import now
from .file import copen
from .filesystem import mdatetime
from .object import args_to_key
from .time import MeasureTime

logger = logging.getLogger(__name__)

PathType = Union[str, PathLike]


def read_pickle(path: PathType) -> Any:

    """Read pickle file from `path`.
    Warning: All usual security consideration regarding the pickle module still apply.
    """

    with copen(path, "rb") as fr:
        return pickle.load(fr)  # nosec


def write_pickle(result: Any, path: PathType, protocol: Optional[int] = None, safe: bool = False) -> None:

    """Write `result` to `path` using pickle serialization.

    `protocol': pickle protocol version
    `safe`: if True, don't overwrite original file in case any error occurs
    """

    with sopen(path, "wb", safe=safe) as fw:
        pickle.dump(result, fw, protocol=protocol)


def read_iter(path: PathType) -> Iterator[Any]:

    """Read pickled iterable from `path`.
    Warning: All usual security consideration regarding the pickle module still apply.
    """

    with copen(path, "rb") as fr:
        unpickler = pickle.Unpickler(fr)  # nosec
        while fr.peek(1):
            yield unpickler.load()


def write_iter(it: Iterable[Any], path: PathType, protocol: Optional[int] = None, safe: bool = False) -> Iterator[Any]:

    """Write iterable `it` to `path` using pickle serialization. This uses much less memory than
            writing a full list at once.
    Read back using `read_iter()`. If `safe` is True, the original file is not overwritten
            if any error occurs.
    This is a generator which yields the values read from `it`. So it must be consumed
            to actually write anything to disk.
    """

    with sopen(path, "wb", safe=safe) as fw:
        pickler = pickle.Pickler(fw, protocol=protocol)
        for result in it:
            pickler.dump(result)
            yield result


def key_to_hash(key: Any, protocol: Optional[int] = None) -> str:
    from hashlib import md5

    binary = pickle.dumps(key, protocol=protocol)
    return md5(binary).hexdigest()  # nosec


def cache(
    path: Path,
    duration: Optional[timedelta] = None,
    generator: bool = False,
    protocol: int = HIGHEST_PROTOCOL,
    ignoreargs: bool = False,
    ignore_first_arg: bool = False,
    keyfunc: Optional[Callable[[tuple, dict], str]] = None,
    consume: bool = False,
    return_cached: bool = False,
    file_ext: Optional[str] = None,
    cached_only: bool = False,
) -> Callable[[Callable], Callable]:

    """Decorator to cache function calls. Doesn't take function arguments into regard.
    It's using `pickle` to deserialize the data. So don't use it with untrusted inputs.

    `path`: path to cache file or directory.
            This can be a template string where `ppv` is assigned the pickle protocol version.
    `duration`: maximum age of cache
    `generator`: set to True to store the results of generator objects
    `protocol`: pickle protocol version

    If `ignoreargs` is True, the cache won't take function arguments into regard.
            The path will be interpreted as template string to a file instead of a directory.
    """

    if not generator and consume:
        raise ValueError("consume can only be used for generator")

    if duration is None:
        _duration = timedelta.max
    else:
        _duration = duration

    def decorator(func):
        # type: (Callable, ) -> Callable

        @wraps(func)
        def inner(*args, **kwargs):
            # type: (*Any, **Any) -> Any

            strpath = fspath(path).format(ppv=protocol)

            if not ignoreargs:
                if ignore_first_arg:
                    args = args[1:]

                _file_ext = file_ext or ".p"

                if keyfunc is None:
                    hashstr = key_to_hash(args_to_key(args, kwargs), protocol=protocol)
                else:
                    hashstr = keyfunc(args, kwargs)
                fullpath = os.path.join(strpath, hashstr + _file_ext)
            else:
                if keyfunc or file_ext:
                    raise ValueError("`keyfunc` or `file_ext` can only be specified if ignoreargs is False")
                if args or kwargs:
                    logger.warning("cache file decorator for %s called with arguments", func.__name__)
                fullpath = strpath

            try:
                invalid = now() - mdatetime(fullpath) > _duration
            except FileNotFoundError:
                invalid = True

            if invalid:

                if cached_only:
                    raise LookupError("Not in cache")

                cached = False
                if not ignoreargs:
                    path.mkdir(parents=True, exist_ok=True)

                if generator and not consume:
                    it = func(*args, **kwargs)
                    logger.debug("Writing iterable to <%s>", fullpath)
                    result: Any = write_iter(it, fullpath, protocol=protocol, safe=True)
                else:
                    with MeasureTime() as m:
                        if generator and consume:
                            result = list(func(*args, **kwargs))
                        else:
                            result = func(*args, **kwargs)
                    logger.debug("Result calculated in %s seconds and written to <%s>", m.get(), fullpath)
                    write_pickle(result, fullpath, protocol=protocol, safe=True)
            else:
                cached = True
                if generator and not consume:
                    logger.debug("Loading iterable from <%s>", fullpath)
                    result = read_iter(fullpath)
                else:
                    with MeasureTime() as m:
                        result = read_pickle(fullpath)
                    logger.debug("Result loaded from <%s> in %s seconds", fullpath, m.get())

            if return_cached:
                return cached, result
            else:
                return result

        return inner

    return decorator


def unpickle(path: PathType, requirements: Iterable[Tuple[str, Optional[str]]] = ()) -> Any:

    """Can be used to unpickle objects when normal unpickling fails to import some dependencies correctly.
    path: Path to the pickled file.
    requirements: Iterable of (module, package) tuples to be imported.

    Consider this scenario:
    ```python
    import pickle
    class asd:
            def qwe():
                    pass
    a = asd()
    with open("asd.p", "wb") as fw:
            pickle.dump(a, fw)

    with open("asd.p", "rb") as fr:
            a = pickle.load(fr)  # everything ok here
    ```

    Now the class definition is moved out of this file into another file `qwe.py`. Then
    ```python
    import pickle
    with open("asd.p", "rb") as fr:
            a = pickle.load(fr)  # AttributeError: Can't get attribute 'asd' on <module '__main__' (built-in)>
    ```

    Now unpickle can be used to fix this problem:
    ```python
    from genutility.pickle import unpickle
    a = unpickle("asd.p", [("qwe", "asd")])
    ```

    Warning: Only use on safe inputs.
    """

    import __main__

    for module, package in requirements:
        mod = importlib.import_module(module, package)
        if package:
            name = package
            type = getattr(mod, package)
        else:
            name = module
            type = mod

        setattr(__main__, name, type)

    with copen(path, "rb") as fr:
        return pickle.load(fr)  # nosec
