from __future__ import absolute_import, division, print_function, unicode_literals

import json
from itertools import islice
from typing import TYPE_CHECKING

from .file import copen

if TYPE_CHECKING:
	from typing import Any, Callable, Dict, Optional, TextIO, Union

if __debug__:
	import jsonschema

class BuiltinEncoder(json.JSONEncoder):
	def default(self, obj):
		from datetime import date

		if isinstance(obj, (set, frozenset)):
			return tuple(obj)
		elif isinstance(obj, complex):
			return [obj.real, obj.imag]
		elif isinstance(obj, date):
			return obj.isoformat()

		return json.JSONEncoder.default(self, obj)

def read_json_schema(path):
	# type: (str, ) -> Dict[str, Any]

	with open(path, "r", encoding="utf-8") as fr:
		return json.load(fr)

def read_json(path, schema=None, object_hook=None):
	# type: (str, Optional[Union[str, dict]]) -> Any

	""" Read the json file at `path` and optionally validates the input according to `schema`.
		The validation requires `jsonschema`.
		`schema` can either be a path as well, or a Python dict which represents the schema.
		`object_hook` is passed through to `json.load`.
	"""

	with copen(path, "rt", encoding="utf-8") as fr:
		obj = json.load(fr, object_hook=object_hook)

	if schema is None:
		return obj

	from jsonschema import validate

	if isinstance(schema, str):
		schema = read_json_schema(schema)

	validate(obj, schema)
	return obj

class json_lines(object):

	""" Read and write files in the JSON Lines format (http://jsonlines.org).
	"""

	def __init__(self,
		stream, doclose,
		cls=None, object_hook=None, parse_float=None, parse_int=None, parse_constant=None, object_pairs_hook=None, **kw
	):
		# type: (TextIO, bool, Optional[json.JSONEncoder], Optional[Callable], Optional[Callable], Optional[Callable], Optional[Callable], Optional[Callable], **Any) -> None

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
		}
		self.json_kwargs.update(kw)

	@staticmethod
	def from_path(
		file, mode="r", encoding="UTF-8", errors="strict", newline=None,
		cls=None, object_hook=None, parse_float=None, parse_int=None, parse_constant=None, object_pairs_hook=None, **kw
	):
		# type: (str, str, int, str, str, Optional[str], bool, Optional[Callable], Optional[json.JSONEncoder], Optional[Callable], Optional[Callable], Optional[Callable], Optional[Callable], Optional[Callable], **Any) -> json_lines

		stream = copen(file, mode, encoding=encoding, errors=errors, newline=newline)
		return json_lines(stream, True, cls, object_hook, parse_float, parse_int, parse_constant, object_pairs_hook, **kw)

	@staticmethod
	def from_stream(
		stream,
		cls=None, object_hook=None, parse_float=None, parse_int=None, parse_constant=None, object_pairs_hook=None, **kw
	):
		# type: (TextIO, Optional[json.JSONEncoder], Optional[Callable], Optional[Callable], Optional[Callable], Optional[Callable], Optional[Callable], **Any) -> json_lines

		return json_lines(stream, False, cls, object_hook, parse_float, parse_int, parse_constant, object_pairs_hook, **kw)

	def __enter__(self):
		# type: () -> None

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
					yield json.loads(line, **self.json_kwargs)
				linenum += 1

		except ValueError as e: # json.JSONDecodeError in python 3.5+
			e.lineno = linenum
			logger.error("JSON Lines parse error in line %s: '%r'", linenum, line)
			raise

	def __iter__(self):
		# type: () -> Iterator

		return self.iterrange()

	def write(self, obj, skipkeys=False, ensure_ascii=False, check_circular=True, allow_nan=True,
		cls=None, indent=None, separators=None, default=None, sort_keys=False, **kw):
		# type: (Any, bool, bool, bool, bool, Optional[Callable], Optional[str], Optional[Tuple[str, str]], Optional[Callable], bool **Any) -> None
		line = json.dumps(obj, skipkeys=skipkeys, ensure_ascii=ensure_ascii, check_circular=check_circular,
			allow_nan=allow_nan, cls=cls, indent=indent, separators=separators, default=default, sort_keys=sort_keys,
			**kw) + self.newline
		self.f.write(line)

	def close(self):
		# type: () -> None

		if self.doclose:
			self.f.close()
