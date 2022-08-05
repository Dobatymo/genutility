from __future__ import generator_stop

from collections import UserDict, defaultdict
from collections.abc import Mapping, MutableMapping  # noqa: F401
from copy import deepcopy
from typing import Any, Callable, Dict, Hashable, Iterable, Iterator, List
from typing import Mapping as MappingT
from typing import MutableMapping as MutableMappingT
from typing import Tuple, TypeVar, Union

T = TypeVar("T")
U = TypeVar("U")
V = TypeVar("V")


def flatten(d: Union[Dict[T, U], List[U], Tuple[U, ...]]) -> Iterator[U]:

    """Flattens dicts/lists of (dicts/lists of ...) lists to lists."""

    if isinstance(d, (list, tuple)):
        yield from d
    elif isinstance(d, dict):
        for k, val in d.items():
            yield from flatten(val)
    else:
        raise TypeError(f"Unsupported type: {type(d)}")


def _flatten_keys(d: Dict[Any, Any], out: Dict[tuple, Any], path: tuple) -> None:

    for k, v in d.items():
        if isinstance(v, dict):
            _flatten_keys(v, out, path + (k,))
        else:
            out[path + (k,)] = v


def flatten_keys(d: Dict[Any, Any]) -> Dict[tuple, Any]:
    out: Dict[tuple, Any] = {}
    _flatten_keys(d, out, ())
    return out


def rec_update(d: MutableMappingT, u: MappingT) -> None:

    """Updates dict `d` recursively with values from `u`.
    Requires `setdefault` method.
    """

    if not isinstance(d, MutableMapping) or not isinstance(u, Mapping):
        raise TypeError("All arguments must be mappings")

    for k, v in u.items():
        if isinstance(v, Mapping):
            rec_update(d.setdefault(k, {}), v)
        else:
            d[k] = v


def rec_update_mod(d: Any, u: MappingT) -> None:

    """Similar to `rec_update`, except that `d` doesn't require the `setdefault` method."""

    for k, v in u.items():
        if isinstance(v, Mapping):
            try:
                sub = d[k]
            except KeyError:
                # d might not store a reference to the original object, thus don't do `sub = d[k] = {}`
                d[k] = {}
                sub = d[k]
            rec_update_mod(sub, v)
        else:
            d[k] = v


def get_one_of(d: Dict[T, U], keys: Iterable[T]) -> Tuple[T, U]:

    """Returns the (key, value) pair of the first key of `keys` found in `d`."""

    for key in keys:
        try:
            return key, d[key]
        except KeyError:
            pass

    raise KeyError("None of the keys could be found")


# similar: subdict
def get_available(d: Dict[T, U], keys: Iterable[T]) -> Iterator[Tuple[T, U]]:

    """Returns all the key-value pairs in `d` for the keys in `it`.
    Missing keys are ignored.
    """

    for key in keys:
        try:
            yield key, d[key]
        except KeyError:
            pass


def subdict(d: MappingT[T, U], it: Iterable[T]) -> Dict[T, U]:

    """Uses the elements of `it` as keys to extract a new sub-dictionary.
    Raises if not all keys in `it` are available.
    """

    return {key: d[key] for key in it}


# was: mapdict, mapget
def mapmap(d: MappingT[T, U], it: Iterable[T]) -> Iterator[U]:
    """Returns all the values of `d` for the keys in `it`.
    Raises for missing keys.
    """

    return (d[i] for i in it)


def hasvalues(d: dict) -> dict:

    """Returns a sub-dictionary which leaves out all pairs where the value evaluates to False."""

    return {k: v for k, v in d.items() if v}


def valuemap(func: Callable[[U], V], d: Dict[T, U]) -> Dict[T, V]:

    """Returns a new dictionary with `func` applied to all values of `d`."""

    return {k: func(v) for k, v in d.items()}


def itemgetter(it: Iterable[T]) -> Callable[[MappingT[T, U]], Iterator[U]]:

    """Similar to `operator.itemgetter` except that it always expects and returns iterables.
    Compare `mapmap`
    """

    return lambda d: (d[i] for i in it)


def subdictdefault(d: MappingT[T, U], it: Iterable[T], default: V = None) -> Dict[T, Union[U, V]]:

    """Uses the elements of `it` as keys to extract a new sub-dictionary."""

    return {key: d.get(key, default) for key in it}


def update(d1: dict, d2: dict) -> None:

    """Same as `dict.update` except that `None` values are skipped."""

    for k, v in d2.items():
        if v is not None:
            d1[k] = v


class keydefaultdict(defaultdict):

    """defaultdict which passes a key to the default factory."""

    def __missing__(self, key: Hashable) -> Any:

        if self.default_factory is None:
            raise KeyError(key)
        else:
            value = self[key] = self.default_factory(key)  # type: ignore[call-arg]
            return value


class KeyExistsError(KeyError):
    pass


class NoOverwriteDict(UserDict):

    """Dictionary which does not allow overwriting existing items."""

    def __setitem__(self, key: Hashable, value: Any) -> None:
        if key in self.data:
            raise KeyExistsError(repr(key))
        self.data[key] = value

    def overwrite(self, key: Hashable, value: Any) -> None:
        self.data[key] = value

    def dict(self):
        return self.data


def _merge_schema(d1: dict, d2: dict) -> None:

    """Merge `d2` into `d1`. `d2` stays unmodified."""

    a = d1.keys()
    b = d2.keys()

    for k in a & b:
        if type(d1[k]) != type(d2[k]):  # noqa: E721
            raise TypeError(f"Type of {k} changed from {type(d1[k])} to {type(d2[k])}")

        if isinstance(d1[k], list):
            if d1[k] and d2[k]:
                if type(d1[k][0]) != type(d2[k][0]):  # noqa: E721
                    raise TypeError(f"Type of list {k} changed from {type(d1[k][0])} to {type(d2[k][0])}")
                if isinstance(d1[k][0], dict):
                    _merge_schema(d1[k][0], d2[k][0])

        elif isinstance(d1[k], dict):
            _merge_schema(d1[k], d2[k])

        elif isinstance(d1[k], int):
            d1[k] = max(d1[k], d2[k])

    for k in b - a:
        if isinstance(d2[k], list):
            d1[k] = deepcopy(d2[k][:1])
        else:
            d1[k] = deepcopy(d2[k])


def _get_intsize(num: int) -> str:
    if num >= 2**63:
        return "uint64"
    elif num >= 2**32:
        return "int64"
    elif num >= 2**31:
        return "uint32"
    else:
        return "int32"


def _post_schema(d: dict) -> None:

    for k in d:
        if isinstance(d[k], dict):
            _post_schema(d[k])
        elif isinstance(d[k], list):
            if d[k]:
                if isinstance(d[k][0], dict):
                    _post_schema(d[k][0])
                elif isinstance(d[k][0], int):
                    d[k][0] = _get_intsize(d[k][0])
                else:
                    d[k][0] = type(d[k][0]).__name__
        elif isinstance(d[k], int):
            d[k] = _get_intsize(d[k])
        else:
            d[k] = type(d[k]).__name__


def get_schema_simple(d: Iterable[dict]) -> dict:
    """Returns a combined schema definition for the dicts provided by iterable `d`.
    - Keys are assumed to be optional.
    - Type unions are not supported. Changing field types will throw an exception.
    - Ints are combined to the largest type (eg. int32->int64)
    - For lists, only the first element is looked at, and it is assumed that all following elements
        are of the same type. This is not verified however.
    """

    schema: Dict[str, Any] = {}
    for i in d:
        _merge_schema(schema, i)

    _post_schema(schema)
    return schema


# was: zipmap
def zipget(objs: Iterable[MappingT[T, U]], keys: Iterable[T]) -> Iterator[U]:

    """Gets a list of keys from a list of mappings.
        zipget([[1, 2], [3, 4]], [0, 1]) -> (1, 4)

    Similar to numpy indexing:
        a = np.array([[1, 2], [3, 4]])
        a[np.arange(len(a)), [0, 1]] -> array([1, 4])
    """

    return (obj[key] for obj, key in zip(objs, keys))
