from datetime import date, datetime, time
from functools import partial
from typing import Any, Iterable, Iterator

from msgpack import ExtType, Packer, Unpacker, pack, packb, unpack, unpackb

from ._files import PathType
from .atomic import sopen
from .file import copen


class EXTID:
    datetime = 1
    set = 2
    frozenset = 3
    date = 4
    time = 5


def default(obj):
    if isinstance(obj, datetime):
        return ExtType(EXTID.datetime, obj.isoformat().encode("utf-8"))  # todo: use struct.Struct instead
    elif isinstance(obj, date):
        return ExtType(EXTID.date, obj.isoformat().encode("utf-8"))  # todo: use struct.Struct instead
    elif isinstance(obj, time):
        return ExtType(EXTID.time, obj.isoformat().encode("utf-8"))  # todo: use struct.Struct instead
    elif isinstance(obj, set):
        return ExtType(EXTID.set, packb(tuple(obj), use_bin_type=True))
    elif isinstance(obj, frozenset):
        return ExtType(EXTID.frozenset, packb(tuple(obj), use_bin_type=True))

    return obj


def ext_hook(code, data):
    if code == EXTID.datetime:
        return datetime.fromisoformat(data.decode("utf-8"))
    elif code == EXTID.date:
        return date.fromisoformat(data.decode("utf-8"))
    elif code == EXTID.time:
        return time.fromisoformat(data.decode("utf-8"))
    elif code == EXTID.set:
        return set(unpackb(data, use_list=False, raw=False))
    elif code == EXTID.frozenset:
        return frozenset(unpackb(data, use_list=False, raw=False))

    return data


dumps = partial(packb, default=default, use_bin_type=True)
loads = partial(unpackb, use_list=False, raw=False, strict_map_key=False, ext_hook=ext_hook)


def key_to_hash(key: Any) -> str:
    from hashlib import md5

    binary = dumps(key)
    return md5(binary).hexdigest()  # nosec


def read_msgpack(path: PathType) -> Any:
    """Read msgpack file from `path`."""

    with copen(path, "rb") as fr:
        return unpack(fr, use_list=False, raw=False, strict_map_key=False, ext_hook=ext_hook)


def write_msgpack(obj: Any, path: PathType, safe: bool = False) -> None:
    """Write `obj` to `path` using msgpack serialization.

    `safe`: if True, don't overwrite original file in case any error occurs
    """

    with sopen(path, "wb", safe=safe) as fw:
        pack(obj, fw, default=default, use_bin_type=True)


def read_iter(path: PathType) -> Iterator[Any]:
    """Read msgpack'd iterable from `path`."""

    with copen(path, "rb") as fr:
        unpacker = Unpacker(fr, use_list=False, raw=False, strict_map_key=False, ext_hook=ext_hook)
        yield from unpacker


def write_iter(it: Iterable[Any], path: PathType, safe: bool = False) -> Iterator[Any]:
    """Write iterable `it` to `path` using msgpack serialization. This uses much less memory than
            writing a full list at once.
    Read back using `read_iter()`. If `safe` is True, the original file is not overwritten
            if any error occurs.
    This is a generator which yields the values read from `it`. So it must be consumed
            to actually write anything to disk.
    """

    with sopen(path, "wb", safe=safe) as fw:
        packer = Packer(default=default, use_bin_type=True)
        for obj in it:
            fw.write(packer.pack(obj))
            yield obj
