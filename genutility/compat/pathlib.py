from __future__ import absolute_import, division, print_function, unicode_literals

from future.utils import PY36_PLUS
from .os import PathLike

try:
	from pathlib import Path, PurePath

	if not PY36_PLUS:
		PurePath.__fspath__ = PurePath.__str__

except ImportError:
	from pathlib2 import Path, PurePath

assert hasattr(PurePath, "__fspath__")
PathLike.register(PurePath)
