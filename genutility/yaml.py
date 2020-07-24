from __future__ import absolute_import, division, print_function, unicode_literals

from builtins import str

from io import open
from typing import TYPE_CHECKING

from ruamel.yaml import YAML

if TYPE_CHECKING:
	from typing import Any

def read_yaml(path):
	# type: (str, ) -> Any

	with open(path, "r", encoding="utf-8") as fr:
		yaml = YAML(typ="safe")
		return yaml.load(fr)

def write_yaml(obj, path):
	# type: (str, Any) -> None

	with open(path, "w", encoding="utf-8") as fw:
		yaml = YAML(typ="safe")
		yaml.dump(obj, fw)
