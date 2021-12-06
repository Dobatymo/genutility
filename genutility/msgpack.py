from __future__ import generator_stop

from datetime import datetime
from functools import partial

from msgpack import ExtType, packb, unpackb

from .compat.datetime import datetime as compat_datetime


class EXTID:
    datetime = 1
    set = 2
    frozenset = 3


def default(obj):
    if isinstance(obj, (datetime, compat_datetime)):
        return ExtType(EXTID.datetime, obj.isoformat().encode("utf-8"))  # todo: use struct.Struct instead
    elif isinstance(obj, set):
        return ExtType(EXTID.set, packb(tuple(obj), use_bin_type=True))
    elif isinstance(obj, frozenset):
        return ExtType(EXTID.frozenset, packb(tuple(obj), use_bin_type=True))

    return obj


def ext_hook(code, data):
    if code == EXTID.datetime:
        return compat_datetime.fromisoformat(data.decode("utf-8"))
    elif code == EXTID.set:
        return set(unpackb(data, use_list=False, raw=False))
    elif code == EXTID.frozenset:
        return frozenset(unpackb(data, use_list=False, raw=False))

    return data


dumps = partial(packb, default=default, use_bin_type=True)
loads = partial(unpackb, ext_hook=ext_hook, use_list=False, raw=False)
