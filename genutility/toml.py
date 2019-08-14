from __future__ import absolute_import, division, print_function, unicode_literals

from builtins import str

from io import open
from typing import TYPE_CHECKING

import toml

if TYPE_CHECKING:
	from typing import Any

def read_toml(path):
	# type: (str, ) -> Any

	with open(path, "r", encoding="utf-8") as fr:
		return toml.load(fr)

def write_toml(obj, path):
	# type: (str, Any) -> None

	with open(path, "w", encoding="utf-8") as fw:
		toml.dump(obj, fw)
