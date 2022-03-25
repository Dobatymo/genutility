from __future__ import generator_stop

from builtins import sorted as _builtin_sorted
from copy import copy
from json import dumps
from typing import Any, List


def cast(object, class_, instanceof=object, *args, **kwargs):
    """Changes the class of `object` to `class_` if `object` is an instance of `instanceof`,
    calls the initializer and returns it.
    """

    object = copy(object)
    if isinstance(object, instanceof):
        object.__class__ = class_
        object.__init__(*args, **kwargs)
    else:
        raise TypeError(f"Object is not an instance of {instanceof.__name__}")
    return object


class STAR:
    pass


def args_to_key(args, kwargs, separator=STAR):
    # type: (tuple, dict, Any) -> tuple

    """Create cache key from function arguments."""

    key = []  # type: List[tuple]
    if args:
        key.extend(args)
    if kwargs:
        key.append(separator)
        key.extend(sorted(kwargs.items()))

    return tuple(key)


def compress(value):
    # type: (Any, ) -> Any

    """Creates a copy of the object where some data structures are replaced with equivalent ones
    which take up less space, but are not necessarily mutable anymore.

    tuple < list
    set == frozenset
    bytes < bytearray
    """

    # sets are not processed because they cannot contain lists or bytearrays anyway.

    if isinstance(value, (tuple, list)):  # tuple *can* contain mutables
        return tuple(compress(x) for x in value)
    elif isinstance(value, bytearray):
        return bytes(value)  # bytearray can only be bytes or List[int] right?
    elif isinstance(value, dict):
        return {k: compress(v) for k, v in value.items()}
    else:
        return value


def _sorted(value: List, *, reverse: bool = False) -> Any:
    def keyfunc(value: Any) -> Any:
        if isinstance(value, dict):
            return dumps(value)
        else:
            return value

    return _builtin_sorted(value, key=keyfunc)


def sorted(value: Any, *, reverse: bool = False) -> Any:
    if isinstance(value, list):
        return _sorted([sorted(v, reverse=reverse) for v in value], reverse=reverse)
    elif isinstance(value, tuple):
        return tuple(_sorted([sorted(v, reverse=reverse) for v in value], reverse=reverse))
    elif isinstance(value, dict):
        return dict(_sorted([(k, sorted(v, reverse=reverse)) for k, v in value.items()], reverse=reverse))
    else:
        return value


if __name__ == "__main__":
    from argparse import ArgumentParser
    from pathlib import Path

    from genutility.json import read_json, write_json

    parser = ArgumentParser(description="Sort json files recursively, both lists and objects")
    parser.add_argument("--inpath", type=Path)
    parser.add_argument("--outpath", type=Path)
    parser.add_argument("--indent")
    args = parser.parse_args()

    obj = read_json(args.inpath)
    write_json(sorted(obj), args.outpath, indent=args.indent)
