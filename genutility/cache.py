import logging
import os
import os.path
from datetime import timedelta
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from .datetime import now
from .filesystem import mdatetime
from .object import args_to_key
from .time import MeasureTime

logger = logging.getLogger(__name__)


def cache(
    path: Path,
    duration: Optional[timedelta] = None,
    generator: bool = False,
    serializer: str = "pickle",
    serializer_kwargs: Optional[Dict[str, Any]] = None,
    deserializer_kwargs: Optional[Dict[str, Any]] = None,
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

    from . import pickle  # nosec

    serializer_kwargs = serializer_kwargs or {}
    deserializer_kwargs = deserializer_kwargs or {}

    if serializer == "pickle":
        from pickle import HIGHEST_PROTOCOL  # nosec

        _serializer_kwargs: Dict[str, Any] = {"protocol": HIGHEST_PROTOCOL, "safe": True}
        _deserializer_kwargs: Dict[str, Any] = {}
        write_iter = pickle.write_iter
        write_file = pickle.write_pickle
        read_iter = pickle.read_iter
        read_file = pickle.read_pickle
        key_to_hash = pickle.key_to_hash
        _hash_sep: Any = None

    elif serializer == "msgpack":
        from . import msgpack

        _serializer_kwargs = {"safe": True}
        _deserializer_kwargs = {}
        write_iter = msgpack.write_iter
        write_file = msgpack.write_msgpack
        read_iter = msgpack.read_iter
        read_file = msgpack.read_msgpack
        key_to_hash = msgpack.key_to_hash
        _hash_sep = None

    elif serializer == "json":
        from . import json

        _serializer_kwargs = {"ensure_ascii": False, "sort_keys": False, "default": None, "safe": True}
        _deserializer_kwargs = {"cls": None, "object_hook": None}
        write_iter = json.write_json_lines
        write_file = json.write_json
        read_iter = json.read_json_lines
        read_file = json.read_json
        key_to_hash = json.key_to_hash
        _hash_sep = {}

    else:
        raise ValueError(f"Invalid serializer: {serializer}")

    _serializer_kwargs.update(serializer_kwargs)
    _deserializer_kwargs.update(deserializer_kwargs)

    _pure_serializer_kwargs = _serializer_kwargs.copy()
    _pure_serializer_kwargs.pop("safe")

    if not generator and consume:
        raise ValueError("consume can only be used for generator")

    if duration is None:
        _duration = timedelta.max
    else:
        _duration = duration

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def inner(*args: Any, **kwargs: Any) -> Any:
            strpath = os.fspath(path).format_map(_serializer_kwargs)

            if not ignoreargs:
                if ignore_first_arg:
                    args = args[1:]

                _file_ext = file_ext or ".p"

                if keyfunc is None:
                    hashstr = key_to_hash(args_to_key(args, kwargs, _hash_sep), **_pure_serializer_kwargs)
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
                    result: Any = write_iter(it, fullpath, **_serializer_kwargs)
                else:
                    with MeasureTime() as m:
                        if generator and consume:
                            result = list(func(*args, **kwargs))
                        else:
                            result = func(*args, **kwargs)
                    logger.debug("Result calculated in %s seconds and written to <%s>", m.get(), fullpath)
                    write_file(result, fullpath, **_serializer_kwargs)
            else:
                cached = True
                if generator and not consume:
                    logger.debug("Loading iterable from <%s>", fullpath)
                    result = read_iter(fullpath, **_deserializer_kwargs)
                else:
                    with MeasureTime() as m:
                        result = read_file(fullpath, **_deserializer_kwargs)
                    logger.debug("Result loaded from <%s> in %s seconds", fullpath, m.get())

            if return_cached:
                return cached, result
            else:
                return result

        return inner

    return decorator
