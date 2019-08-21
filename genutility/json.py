from __future__ import absolute_import, division, print_function, unicode_literals

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from typing import Any, Dict, Optional, Union

if __debug__:
	import jsonschema

class BuiltinEncoder(json.JSONEncoder):
	def default(self, obj):
		if isinstance(obj, (set, frozenset)):
			return tuple(obj)
		elif isinstance(obj, complex):
			return [obj.real, obj.imag]

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

	with open(path, "r", encoding="utf-8") as fr:
		obj = json.load(fr, object_hook=object_hook)

	if schema is None:
		return obj

	from jsonschema import validate

	if isinstance(schema, str):
		schema = read_json_schema(schema)

	validate(obj, schema)
	return obj
