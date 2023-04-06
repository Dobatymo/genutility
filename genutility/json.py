import csv
import datetime
import json
import logging
from functools import partial
from itertools import islice
from pathlib import Path
from types import ModuleType
from typing import IO, Any, Callable, Dict, FrozenSet, Iterable, Iterator, Optional, Sequence, Tuple, Type, Union

from typing_extensions import TypedDict  # typing.TypedDict is available in Python 3.8+

from .atomic import sopen
from .datetime import datetime_from_utc_timestamp_ms, now
from .file import copen

PathStr = Union[Path, str]
JsonDict = Dict[str, Any]

logger = logging.getLogger(__name__)


class BuiltinEncoder(json.JSONEncoder):
    def __init__(self, *args: Any, sort_sets: bool = False, **kwargs: Any) -> None:
        json.JSONEncoder.__init__(self, *args, **kwargs)
        self.sort_sets = sort_sets

    def default(self, obj):
        # collections.OrderedDict is supported by default

        from base64 import b85encode
        from uuid import UUID

        if isinstance(obj, (set, frozenset)):
            if self.sort_sets:
                return sorted(obj)
            else:
                return tuple(obj)
        elif isinstance(obj, complex):
            return [obj.real, obj.imag]
        elif isinstance(obj, (datetime.date, datetime.time, datetime.datetime)):
            return obj.isoformat()
        elif isinstance(obj, datetime.timedelta):
            return obj.total_seconds()
        elif isinstance(obj, UUID):
            return str(obj)
        elif isinstance(obj, bytes):
            return b85encode(obj).decode("ascii")  # b85encode doesn't use ", ' or \

        return json.JSONEncoder.default(self, obj)


class BuiltinRoundtripEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.timedelta):
            return {"$timedelta": (obj.days, obj.seconds, obj.microseconds)}
        elif isinstance(obj, datetime.datetime):
            return {"$datetime": obj.isoformat()}
        elif isinstance(obj, datetime.date):
            return {"$dateobj": obj.isoformat()}
        elif isinstance(obj, set):
            return {"$set": tuple(obj)}
        elif isinstance(obj, frozenset):
            return {"$frozenset": tuple(obj)}

        return json.JSONEncoder.default(self, obj)


class BuiltinRoundtripDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(self, object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, obj):
        if len(obj) == 1:
            key, value = next(iter(obj.items()))
            if key == "$timedelta":
                return datetime.timedelta(*value)
            elif key == "$datetime":
                return datetime.datetime.fromisoformat(value)
            elif key == "$date":  # for compatibility with bson.json_util
                return datetime_from_utc_timestamp_ms(value)
            elif key == "$dateobj":
                return datetime.date.fromisoformat(value)
            elif key == "$set":
                return set(value)
            elif key == "$frozenset":
                return frozenset(value)

        return obj


def read_json_schema(path: PathStr) -> JsonDict:
    with open(path, encoding="utf-8") as fr:
        return json.load(fr)


def read_json(
    path: PathStr,
    schema: Optional[Union[str, JsonDict]] = None,
    cls: Optional[Type[json.JSONDecoder]] = None,
    object_hook: Any = None,
) -> Any:
    """Read the json file at `path` and optionally validates the input according to `schema`.
    The validation requires `jsonschema`.
    `schema` can either be a path as well, or a Python dict which represents the schema.
    `cls` and `object_hook` is passed through to `json.load`.
    """

    with copen(path, "rt", encoding="utf-8") as fr:
        obj = json.load(fr, cls=cls, object_hook=object_hook)

    if schema is None:
        return obj

    from jsonschema import validate

    if isinstance(schema, str):
        schema = read_json_schema(schema)

    validate(obj, schema)
    return obj


def write_json(
    obj: Any,
    path: PathStr,
    mode: str = "wt",
    schema: Optional[Union[str, JsonDict]] = None,
    ensure_ascii: bool = False,
    cls: Optional[Type[json.JSONEncoder]] = None,
    indent: Optional[Union[str, int]] = None,
    sort_keys: bool = False,
    default: Optional[Callable] = None,
    safe: bool = False,
    **kw: Any,
) -> None:
    """Writes python object `obj` to `path` as json files and optionally validates the object
    according to `schema`. The validation requires `jsonschema`.
    The remaining optional parameters are passed through to `json.dump`.
    `safe`: if True, don't overwrite original file in case any error occurs
    """

    if schema:
        from jsonschema import validate

        if isinstance(schema, str):
            schema = read_json_schema(schema)

        validate(obj, schema)

    with sopen(path, mode, encoding="utf-8", safe=safe) as fw:
        json.dump(
            obj, fw, ensure_ascii=ensure_ascii, cls=cls, indent=indent, sort_keys=sort_keys, default=default, **kw
        )


class JsonLoadKwargs(TypedDict):
    cls: Optional[Type[json.JSONDecoder]]
    object_hook: Optional[Callable]
    parse_float: Optional[Callable]
    parse_int: Optional[Callable]
    parse_constant: Optional[Callable]
    object_pairs_hook: Optional[Callable]


class json_lines:

    """Read and write files in the JSON Lines format (http://jsonlines.org)."""

    def __init__(
        self,
        stream: IO,
        doclose: bool,
        cls: Optional[Type[json.JSONDecoder]] = None,
        object_hook: Optional[Callable] = None,
        parse_float: Optional[Callable] = None,
        parse_int: Optional[Callable] = None,
        parse_constant: Optional[Callable] = None,
        object_pairs_hook: Optional[Callable] = None,
        **kw: Any,
    ) -> None:
        """Don't use directly. Use `from_path` or `from_stream` classmethods instead."""

        """ fixme: how should `close` be handled?
            1: If you don't want to close `stream`, just don't call `close()` or use as context manager.
            2: use `doclose` argument to decide
        """

        self.f = stream
        self.doclose = doclose
        self.newline = "\n"

        self.json_kwargs: JsonLoadKwargs = {
            "cls": cls,
            "object_hook": object_hook,
            "parse_float": parse_float,
            "parse_int": parse_int,
            "parse_constant": parse_constant,
            "object_pairs_hook": object_pairs_hook,
        }
        self.json_cls_kw = kw

    @staticmethod
    def from_path(
        file: PathStr,
        mode: str = "rt",
        encoding: str = "utf-8",
        errors: str = "strict",
        newline: Optional[str] = None,
        cls: Optional[Type[json.JSONDecoder]] = None,
        object_hook: Optional[Callable] = None,
        parse_float: Optional[Callable] = None,
        parse_int: Optional[Callable] = None,
        parse_constant: Optional[Callable] = None,
        object_pairs_hook: Optional[Callable] = None,
        **kw: Any,
    ) -> "json_lines":
        """Binary writing modes "wb", "ab", "r+b", "w+b" are not supported by the python json module.
        Use text modes instead. Binary read-only is fine.
        """

        if isinstance(file, str):
            if file.startswith("s3://"):
                message = f"""Reading data from S3 is not supported natively. Use `smart-open` package:
```python
from smart_open import open
with open("{file}", "r") as fr:
    with json_lines.from_stream(fr) as jl:
        for doc in jl:
            pass
```"""
                raise ValueError(message)

        if set(mode) not in (set("rt"), set("rb"), set("xt"), set("xb"), set("wt"), set("at"), set("r+t"), set("w+t")):
            raise ValueError(f"mode cannot be `{mode}`")

        stream = copen(file, mode, encoding=encoding, errors=errors, newline=newline)
        return json_lines(
            stream, True, cls, object_hook, parse_float, parse_int, parse_constant, object_pairs_hook, **kw
        )

    @staticmethod
    def from_stream(
        stream: IO,
        cls: Optional[Type[json.JSONDecoder]] = None,
        object_hook: Optional[Callable] = None,
        parse_float: Optional[Callable] = None,
        parse_int: Optional[Callable] = None,
        parse_constant: Optional[Callable] = None,
        object_pairs_hook: Optional[Callable] = None,
        **kw: Any,
    ) -> "json_lines":
        return json_lines(
            stream, False, cls, object_hook, parse_float, parse_int, parse_constant, object_pairs_hook, **kw
        )

    def __enter__(self) -> "json_lines":
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def iterrange(self, start: int = 0, stop: Optional[int] = None) -> Iterator:
        try:
            import simplejson as sjson

            _json: ModuleType = sjson
        except ImportError:
            _json = json

        linenum = start + 1
        try:
            for line in islice(self.f, start, stop):
                line = line.rstrip().lstrip("\x00")  # fixme: strip \0 is only a temp fix!
                if line:
                    yield _json.loads(line, **self.json_kwargs, **self.json_cls_kw)
                linenum += 1

        except json.JSONDecodeError as e:
            e.lineno = linenum
            logger.error("JSON Lines parse error in line %s: '%r'", linenum, line)
            raise

    def __iter__(self) -> Iterator:
        return self.iterrange()

    def write(
        self,
        obj: Any,
        skipkeys: bool = False,
        ensure_ascii: bool = False,
        check_circular: bool = True,
        allow_nan: bool = True,
        cls: Optional[Type[json.JSONEncoder]] = None,
        separators: Optional[Tuple[str, str]] = None,
        default: Optional[Callable] = None,
        sort_keys: bool = False,
        **kw: Any,
    ) -> None:
        json.dump(
            obj,
            self.f,
            skipkeys=skipkeys,
            ensure_ascii=ensure_ascii,
            check_circular=check_circular,
            allow_nan=allow_nan,
            cls=cls,
            indent=None,
            separators=separators,
            default=default,
            sort_keys=sort_keys,
            **kw,
        )
        self.f.write(self.newline)

    def writelines(
        self,
        objs: Iterable[Any],
        skipkeys: bool = False,
        ensure_ascii: bool = False,
        check_circular: bool = True,
        allow_nan: bool = True,
        cls: Optional[Type[json.JSONEncoder]] = None,
        separators: Optional[Tuple[str, str]] = None,
        default: Optional[Callable] = None,
        sort_keys: bool = False,
        **kw: Any,
    ) -> None:
        for obj in objs:
            self.write(obj)

    def close(self) -> None:
        if self.doclose:
            self.f.close()


def read_json_lines(
    file: PathStr, cls: Optional[Type[json.JSONDecoder]] = None, object_hook: Optional[Callable] = None
) -> Iterator[Any]:
    """Iterate over a JSON Lines `file` object by object.
    `object_hook` is passed through to `json.load`.
    """

    with json_lines.from_path(file, mode="rt", cls=cls, object_hook=object_hook) as fr:
        yield from fr


def write_json_lines(
    it: Iterable[Any],
    path,
    ensure_ascii: bool = False,
    sort_keys: bool = False,
    default: Optional[Callable] = None,
    safe: bool = False,
) -> Iterator[Any]:
    with sopen(path, "wt", encoding="utf-8", safe=safe) as fw:
        with json_lines.from_stream(fw, ensure_ascii=ensure_ascii, sort_keys=sort_keys, default=default) as fw:
            for obj in it:
                fw.write(obj)
                yield obj


def jl_to_csv(jlpath: PathStr, csvpath: str, keyfunc: Callable[[JsonDict], Sequence[str]], mode: str = "xt") -> None:
    with json_lines.from_path(jlpath, "rt") as fr:
        with open(csvpath, mode, encoding="utf-8", newline="") as csvfile:
            fw = csv.writer(csvfile)
            for obj in fr:
                fw.writerow(keyfunc(obj))


def key_to_hash(
    key: Any, ensure_ascii: bool = False, sort_keys: bool = False, default: Optional[Callable] = None
) -> str:
    from hashlib import md5

    binary = json.dumps(key, ensure_ascii=ensure_ascii, sort_keys=sort_keys, default=default).encode("utf-8")
    return md5(binary).hexdigest()  # nosec


class JsonLinesFormatter(logging.Formatter):

    """A JSON Lines formatter for the Python logging library.
    It expects a `dict` as logging message.
    For example:
            logger = logging.getLogger("jsonlines-test")
            handler = logging.StreamHandler()
            formatter = JsonLinesFormatter()
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.warning({"msg": "Hello world!", "level": "greeting"})
    """

    myfields = {
        "datetime": now,  # requires non-default json serializer
        "datetime-str": lambda: now().isoformat(),  # note: lambda required
    }

    def __init__(
        self,
        include: FrozenSet[str] = frozenset(),
        builtins: FrozenSet[str] = frozenset(),
        default: Optional[Callable] = None,
    ) -> None:
        logging.Formatter.__init__(self)
        self.include_b = include & self.myfields.keys()
        self.builtins = builtins
        self.dumps = partial(json.dumps, ensure_ascii=False, indent=None, sort_keys=True, default=default)

    def format(self, record):
        # add builtins logger fields
        row = {name: getattr(record, name) for name in self.builtins}

        # add custom logger fields
        if self.include_b:
            row.update({k: self.myfields[k]() for k in self.include_b})

        # add message fields
        row.update(record.msg)

        return self.dumps(row)
