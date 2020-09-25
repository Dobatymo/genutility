from __future__ import absolute_import, division, print_function, unicode_literals

import os.path
from configparser import ConfigParser
from io import open
from typing import TYPE_CHECKING

from .compat import FileNotFoundError
from .compat.importlib.util import find_spec
from .os import get_appdata_dir

if TYPE_CHECKING:
	from typing import Any, Dict, Optional, Union

if __debug__:
	import jsonschema
	import sortedcontainers

def sort_config(inpath, outpath):
	# type: (str, str) -> None

	from sortedcontainers import SortedDict

	config = ConfigParser(dict_type=SortedDict)
	config.read(inpath, encoding="utf-8")
	with open(outpath, "wt", encoding="utf-8") as fw:
		config.write(fw)

def _load(name):
	# type: (str, ) -> Dict[str, Any]

	from .toml import read_toml

	configfilename = name+".toml"

	# try appdata directory
	try:
		return read_toml(os.path.join(get_appdata_dir(), name, configfilename))
	except FileNotFoundError:
		pass

	# try module directory
	try:
		spec = find_spec(name)

		if spec is None:
			raise ImportError("No module named '{}'".format(name)) # or FileNotFoundError?

		if spec.has_location:
			modpath = os.path.dirname(spec.origin)
		else:
			try:
				modpath = spec.submodule_search_locations[0]
			except (TypeError, IndexError):
				raise FileNotFoundError

		return read_toml(os.path.join(modpath, configfilename))
	except (ImportError, FileNotFoundError):
		pass

	# try working directory
	try:
		return read_toml(configfilename)
	except FileNotFoundError:
		raise FileNotFoundError("{} could not be found in application data, module path or current directory".format(configfilename))

def load(name, json_schema=None):
	# type: (str, Optional[Union[dict, str]]) -> Dict[str, Any]

	from .json import read_json_schema

	obj = _load(name)

	if json_schema is None:
		return obj

	from jsonschema import validate

	if isinstance(json_schema, str):
		json_schema = read_json_schema(json_schema)

	validate(obj, json_schema)
	return obj
