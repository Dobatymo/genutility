from __future__ import absolute_import, division, print_function, unicode_literals

import pickle  # nosec
from functools import wraps
from datetime import timedelta
from typing import TYPE_CHECKING

from .atomic import TransactionalCreateFile
from .compat import FileNotFoundError
from .datetime import now
from .file import copen
from .filesystem import mdatetime
from .object import args_to_key

if TYPE_CHECKING:
	from typing import Any, Callable, Optional, Iterator, Iterable
	from .compat.pathlib import Path

def read_pickle(path):
	# type: (str, ) -> Any

	""" Read pickle file from `path`.
		Warning: All usual security consideration regarding the pickle module still apply.
	"""

	with copen(path, "rb") as fr:
		return pickle.load(fr)  # nosec

def write_pickle(result, path, protocol=None, safe=False):
	# type: (Any, str, Optional[int], bool) -> None

	""" Write `result` to `path` using pickle serialization.

		`protocol': pickle protocol version
		`safe`: if True, don't overwrite original file in case any error occurs
	"""

	if safe:
		context = TransactionalCreateFile
	else:
		context = copen

	with context(path, "wb") as fw:
		pickle.dump(result, fw, protocol=protocol)

def read_iter(path):
	# type: (str, ) -> Iterator[Any]

	""" Read pickled iterable from `path`. 
		Warning: All usual security consideration regarding the pickle module still apply.
	"""

	with copen(path, "rb") as fr:
		unpickler = pickle.Unpickler(fr)  # nosec
		while fr.peek(1):
			yield unpickler.load()

def write_iter(it, path, protocol=None, safe=False):
	# type: (Iterable[Any], str, Optional[int], bool) -> Iterator[Any]

	""" Write iterable `it` to `path` using pickle serialization. This uses much less memory than
			writing a full list at once.
		Read back using `read_iter()`. If `safe` is True, the original file is not overwritten
			if any error occurs.
		This is a generator which yields the values read from `it`. So it must be consumed
			to actually write anything to disk.
	"""

	if safe:
		context = TransactionalCreateFile
	else:
		context = copen

	with context(path, "wb") as fw:
		pickler = pickle.Pickler(fw, protocol=protocol)
		for result in it:
			pickler.dump(result)
			yield result

def key_to_hash(key, protocol=None):
	from hashlib import md5
	binary = pickle.dumps(key, protocol=protocol)
	return md5(binary).hexdigest()  # nosec

def cache(path, duration=None, generator=False, protocol=None):
	# type: (Path, Optional[timedelta], bool, Optional[int]) -> Callable[[Callable], Callable]

	""" Decorator to cache function calls. Doesn't take function arguments into regard.
		It's using `pickle` to deserialize the data. So don't use it with untrusted inputs.

		`path`: path to cache file
		`duration`: maximum age of cache
		`generator`: set to True to store the results of generator objects
		`protocol`: pickle protocol version
	"""

	duration = duration or timedelta.max

	def decorator(func):
		# type: (Callable, ) -> Callable

		@wraps(func)
		def inner(*args, **kwargs):
			# type: (*Any, **Any) -> Any

			hash = key_to_hash(args_to_key(args, kwargs), protocol=protocol)
			fullpath = path / hash

			try:
				invalid = now() - mdatetime(fullpath) > duration
			except FileNotFoundError:
				invalid = True

			if invalid:
				path.mkdir(parents=True, exist_ok=True)
				if generator:
					it = func(*args, **kwargs)
					return write_iter(it, fullpath, protocol=protocol, safe=True)
				else:
					result = func(*args, **kwargs)
					write_pickle(result, fullpath, protocol=protocol, safe=True)
					return result
			else:
				if generator:
					return read_iter(fullpath)
				else:
					return read_pickle(fullpath)
		return inner
	return decorator
