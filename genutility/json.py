from __future__ import generator_stop

import csv
import json
import logging
from datetime import timedelta
from functools import partial, wraps
from itertools import islice
from typing import IO, TYPE_CHECKING, Any, Callable, Dict, FrozenSet, Iterator, Optional, Sequence, Tuple, Type, Union

from typing_extensions import TypedDict

from .atomic import TransactionalCreateFile, sopen
from .datetime import now
from .file import copen
from .filesystem import mdatetime
from .object import args_to_key

if TYPE_CHECKING:
	from pathlib import Path

	PathStr = Union[Path, str]

JsonDict = Dict[str, Any]

logger = logging.getLogger(__name__)

class BuiltinEncoder(json.JSONEncoder):

	def default(self, obj):

		# collections.OrderedDict is supported by default

		from base64 import b85encode
		from datetime import date, timedelta
		from uuid import UUID

		if isinstance(obj, (set, frozenset)):
			return tuple(obj)
		elif isinstance(obj, complex):
			return [obj.real, obj.imag]
		elif isinstance(obj, date):
			return obj.isoformat()
		elif isinstance(obj, timedelta):
			return obj.total_seconds()
		elif isinstance(obj, UUID):
			return str(obj)
		elif isinstance(obj, bytes):
			return b85encode(obj).decode("ascii") # b85encode doesn't use ", ' or \

		return json.JSONEncoder.default(self, obj)

def read_json_schema(path):
	# type: (PathStr, ) -> JsonDict

	with open(path, "r", encoding="utf-8") as fr:
		return json.load(fr)

def read_json(path, schema=None, cls=None, object_hook=None):
	# type: (PathStr, Optional[Union[str, JsonDict]], Any, Any) -> Any

	""" Read the json file at `path` and optionally validates the input according to `schema`.
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

def write_json(obj, path, schema=None, ensure_ascii=False, cls=None, indent=None, sort_keys=False, default=None, safe=False):
	# type: (Any, PathStr, Optional[Union[str, JsonDict]], bool, Optional[Type[json.JSONEncoder]], Optional[Union[str, int]], bool, Optional[Callable], bool) -> None

	""" Writes python object `obj` to `path` as json files and optionally validates the object
		according to `schema`. The validation requires `jsonschema`.
		The remaining optional parameters are passed through to `json.dump`.
		`safe`: if True, don't overwrite original file in case any error occurs
	"""

	if schema:
		from jsonschema import validate

		if isinstance(schema, str):
			schema = read_json_schema(schema)

		validate(obj, schema)

	with sopen(path, "wt", encoding="utf-8", safe=safe) as fw:
		json.dump(obj, fw, ensure_ascii=ensure_ascii, cls=cls, indent=indent, sort_keys=sort_keys, default=default)

class JsonLoadKwargs(TypedDict):
	cls: Optional[Type[json.JSONDecoder]]
	object_hook: Optional[Callable]
	parse_float: Optional[Callable]
	parse_int: Optional[Callable]
	parse_constant: Optional[Callable]
	object_pairs_hook: Optional[Callable]

class json_lines(object):

	""" Read and write files in the JSON Lines format (http://jsonlines.org).
	"""

	def __init__(self,
		stream, doclose, cls=None, object_hook=None, parse_float=None,
		parse_int=None, parse_constant=None, object_pairs_hook=None, **kw
	):
		# type: (IO, bool, Optional[Type[json.JSONDecoder]], Optional[Callable], Optional[Callable], Optional[Callable], Optional[Callable], Optional[Callable], **Any) -> None

		""" Don't use directly. Use `from_path` or `from_stream` classmethods instead. """

		""" fixme: how should `close` be handled?
			1: If you don't want to close `stream`, just don't call `close()` or use as context manager.
			2: use `doclose` argument to decide
		"""

		self.f = stream
		self.doclose = doclose
		self.newline = "\n"

		self.json_kwargs = {
			"cls": cls,
			"object_hook": object_hook,
			"parse_float": parse_float,
			"parse_int": parse_int,
			"parse_constant": parse_constant,
			"object_pairs_hook": object_pairs_hook,
		}  # type: JsonLoadKwargs
		self.json_cls_kw = kw

	@staticmethod
	def from_path(
		file, mode="rt", encoding="utf-8", errors="strict", newline=None,
		cls=None, object_hook=None, parse_float=None, parse_int=None, parse_constant=None, object_pairs_hook=None, **kw
	):
		# type: (PathStr, str, str, str, Optional[str], Optional[Type[json.JSONDecoder]], Optional[Callable], Optional[Callable], Optional[Callable], Optional[Callable], Optional[Callable], **Any) -> json_lines

		""" Binary writing modes "wb", "ab", "r+b", "w+b" are not supported by the python json module.
			Use text modes instead. Binary read-only is fine.
		"""

		if set(mode) not in (set("rt"), set("rb"), set("xt"), set("xb"), set("wt"), set("at"), set("r+t"), set("w+t")):
			raise ValueError(f"mode cannot be `{mode}`")

		stream = copen(file, mode, encoding=encoding, errors=errors, newline=newline)
		return json_lines(stream, True, cls, object_hook, parse_float, parse_int, parse_constant, object_pairs_hook, **kw)

	@staticmethod
	def from_stream(
		stream,
		cls=None, object_hook=None, parse_float=None, parse_int=None, parse_constant=None, object_pairs_hook=None, **kw
	):
		# type: (IO, Optional[Type[json.JSONDecoder]], Optional[Callable], Optional[Callable], Optional[Callable], Optional[Callable], Optional[Callable], **Any) -> json_lines

		return json_lines(stream, False, cls, object_hook, parse_float, parse_int, parse_constant, object_pairs_hook, **kw)

	def __enter__(self):
		# type: () -> json_lines

		return self

	def __exit__(self, exc_type, exc_value, traceback):
		self.close()

	def iterrange(self, start=0, stop=None):
		# type: (int, Optional[int]) -> Iterator

		linenum = start+1
		try:
			for line in islice(self.f, start, stop):
				line = line.rstrip().lstrip("\x00") # fixme: strip \0 is only a temp fix!
				if line:
					yield json.loads(line, **self.json_kwargs, **self.json_cls_kw)
				linenum += 1

		except json.JSONDecodeError as e:
			e.lineno = linenum
			logger.error("JSON Lines parse error in line %s: '%r'", linenum, line)
			raise

	def __iter__(self):
		# type: () -> Iterator

		return self.iterrange()

	def write(self, obj, skipkeys=False, ensure_ascii=False, check_circular=True, allow_nan=True,
		cls=None, separators=None, default=None, sort_keys=False, **kw):
		# type: (Any, bool, bool, bool, bool, Optional[Type[json.JSONEncoder]], Optional[Tuple[str, str]], Optional[Callable], bool, **Any) -> None

		json.dump(obj, self.f, skipkeys=skipkeys, ensure_ascii=ensure_ascii, check_circular=check_circular,
			allow_nan=allow_nan, cls=cls, indent=None, separators=separators, default=default, sort_keys=sort_keys,
			**kw)
		self.f.write(self.newline)

	def close(self):
		# type: () -> None

		if self.doclose:
			self.f.close()

def read_json_lines(file, object_hook=None):
	# type: (PathStr, Optional[Callable]) -> Iterator[Any]

	""" Iterate over a JSON Lines `file` object by object.
		`object_hook` is passed through to `json.load`.
	"""

	with json_lines.from_path(file, mode="rt", object_hook=object_hook) as fr:
		for obj in fr:
			yield obj

def jl_to_csv(jlpath, csvpath, keyfunc, mode="xt"):
	# type: (PathStr, str, Callable[[JsonDict], Sequence[str]], str) -> None

	with json_lines.from_path(jlpath, "rt") as fr:
		with open(csvpath, mode, encoding="utf-8", newline="") as csvfile:
			fw = csv.writer(csvfile)
			for obj in fr:
				fw.writerow(keyfunc(obj))

def key_to_hash(key, default=None):
	# type: (Any, Optional[Callable]) -> str

	from hashlib import md5
	binary = json.dumps(key, default=default).encode("utf-8")
	return md5(binary).hexdigest()  # nosec

def cache(path, duration=None, ensure_ascii=False, indent=None, sort_keys=False, default=None, object_hook=None):
	# type: (Path, Optional[timedelta], bool, Optional[Union[str, int]], bool, Optional[Callable], Optional[Callable]) -> Callable

	""" Decorator to cache results of function to json files at `path` for `duration`.
		The remaining parameters are passed through to `json.dump`.
	"""

	duration = duration or timedelta.max

	def decorator(func):
		# type: (Callable, ) -> Callable

		@wraps(func)
		def inner(*args, **kwargs):

			hash = key_to_hash(args_to_key(args, kwargs, {}), default=default)
			fullpath = path / hash

			try:
				invalid = now() - mdatetime(fullpath) > duration
			except FileNotFoundError:
				invalid = True

			if invalid:
				path.mkdir(parents=True, exist_ok=True)
				ret = func(*args, **kwargs)
				write_json(ret, fullpath, ensure_ascii=ensure_ascii, indent=indent, sort_keys=sort_keys, default=default, safe=True)
				return ret
			else:
				return read_json(fullpath, object_hook=object_hook)

		return inner
	return decorator

def jsonlines_cache(path, duration=None, ensure_ascii=False, sort_keys=False, default=None, object_hook=None):
	# type: (Path, Optional[timedelta], bool, bool, Optional[Callable], Optional[Callable]) -> Callable

	""" Decorator to cache results of function to jsonlines files at `path` for `duration`.
		The remaining parameters are passed through to `json_lines.from_path`.
	"""

	duration = duration or timedelta.max

	def decorator(func):
		# type: (Callable, ) -> Callable

		@wraps(func)
		def inner(*args, **kwargs):

			hash = key_to_hash(args_to_key(args, kwargs, {}), default=default)
			fullpath = path / hash

			try:
				invalid = now() - mdatetime(fullpath) > duration
			except FileNotFoundError:
				invalid = True

			if invalid:
				path.mkdir(parents=True, exist_ok=True)
				with TransactionalCreateFile(fullpath, "wt") as stream:
					with json_lines.from_stream(stream, ensure_ascii=ensure_ascii, sort_keys=sort_keys, default=default) as fw:
						# if `func` raises, TransactionalCreateFile makes sure that the original
						# cache file remains unmodified and that temporary files are deleted
						for obj in func(*args, **kwargs):
							fw.write(obj)
							yield obj
			else:
				with json_lines.from_path(fullpath, "rt", object_hook=object_hook) as fr:
					for obj in fr:
						yield obj

		return inner
	return decorator

class JsonLinesFormatter(logging.Formatter):

	""" A JSON Lines formatter for the Python logging library.
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
		"datetime": now, # requires non-default json serializer
		"datetime-str": lambda: now().isoformat(),
	}

	def __init__(self, include=frozenset(), builtins=frozenset(), default=None):
		# type: (FrozenSet[str], FrozenSet[str], Optional[Callable]) -> None

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
