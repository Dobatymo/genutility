from __future__ import absolute_import, division, print_function, unicode_literals

import pickle  # nosec
from functools import wraps
from typing import TYPE_CHECKING

from .twothree import FileNotFoundError
from .file import copen, OpenFileAndDeleteOnError

if TYPE_CHECKING:
	from typing import Any, Callable

def cache(path, protocol=None):
	# type: (str, int) -> Callable[[Callable], Callable]

	""" Decorator to cache function calls. Doesn't take function arguments into regard.
		It's using `pickle` to deserialize the data. So don't use it with untrusted inputs.
	"""

	def decorator(func):
		# type: (Callable, ) -> Callable

		@wraps(func)
		def inner(*args, **kwargs):
			# type: (*Any, **Any) -> Any

			try:
				with copen(path, "rb") as fr:
					return pickle.load(fr)  # nosec
			except FileNotFoundError:
				result = func(*args, **kwargs)
				with OpenFileAndDeleteOnError(path, "wb") as fw:
					# if pickling fails, the file will be deleted
					# and no incomplete file will be left on the disk
					pickle.dump(result, fw, protocol=protocol)
				return result
		return inner
	return decorator
