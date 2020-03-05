from __future__ import absolute_import, division, print_function, unicode_literals

import pickle  # nosec
from functools import wraps
from datetime import timedelta
from typing import TYPE_CHECKING

from .twothree import FileNotFoundError
from .file import copen
from .atomic import TransactionalCreateFile
from .filesystem import mdatetime

if TYPE_CHECKING:
	from typing import Any, Callable

def read_pickle(path, buffers=None):
	with open(path, "rb") as fr:
		return pickle.load(fr, buffers=buffers)

def cache(path, duration=None, protocol=None):
	# type: (str, Optional[timedelta], int) -> Callable[[Callable], Callable]

	""" Decorator to cache function calls. Doesn't take function arguments into regard.
		It's using `pickle` to deserialize the data. So don't use it with untrusted inputs.
	"""

	duration = duration or timedelta.max

	def decorator(func):
		# type: (Callable, ) -> Callable

		@wraps(func)
		def inner(*args, **kwargs):
			# type: (*Any, **Any) -> Any
			try:
				invalid = now() - mdatetime(path) > duration
			except FileNotFoundError:
				invalid = True

			if invalid:
				result = func(*args, **kwargs)
				with TransactionalCreateFile(path, "wb") as fw:
					# if pickling fails, the file will be deleted
					# and no incomplete file will be left on the disk
					pickle.dump(result, fw, protocol=protocol)
				return result
			else:
				with copen(path, "rb") as fr:
					return pickle.load(fr)  # nosec
		return inner
	return decorator
