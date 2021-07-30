from __future__ import generator_stop

import logging
import pickle  # nosec
from datetime import timedelta
from functools import wraps
from os import fspath
from pickle import HIGHEST_PROTOCOL  # nosec
from typing import TYPE_CHECKING

from .atomic import sopen
from .compat.contextlib import nullcontext
from .datetime import now
from .file import copen
from .filesystem import mdatetime
from .object import args_to_key
from .time import PrintStatementTime

if TYPE_CHECKING:
	from pathlib import Path
	from typing import Any, Callable, Iterable, Iterator, Optional

logger = logging.getLogger(__name__)

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

	with sopen(path, "wb", safe=safe) as fw:
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

	with sopen(path, "wb", safe=safe) as fw:
		pickler = pickle.Pickler(fw, protocol=protocol)
		for result in it:
			pickler.dump(result)
			yield result

def key_to_hash(key, protocol=None):
	from hashlib import md5
	binary = pickle.dumps(key, protocol=protocol)
	return md5(binary).hexdigest()  # nosec

def cache(path, duration=None, generator=False, protocol=HIGHEST_PROTOCOL, ignoreargs=False, verbose=False, keyfunc=None, consume=False):
	# type: (Path, Optional[timedelta], bool, int, bool, bool, Optional[Callable[[tuple, dict], str]], bool) -> Callable[[Callable], Callable]

	""" Decorator to cache function calls. Doesn't take function arguments into regard.
		It's using `pickle` to deserialize the data. So don't use it with untrusted inputs.

		`path`: path to cache file
		`duration`: maximum age of cache
		`generator`: set to True to store the results of generator objects
		`protocol`: pickle protocol version
		`verbose`: print loading times if `generator` is False

		If `ignoreargs` is True, the cache won't take function arguments into regard.
			The path will be interpreted as template string to a file instead of a directory
			where `ppv` is assigned the  pickle protocol version.
	"""

	if not generator and consume:
		raise ValueError("consume can onlt be used for generator")

	if duration is None:
		_duration = timedelta.max
	else:
		_duration = duration

	if not verbose:
		context = nullcontext
	else:
		context = PrintStatementTime

	def decorator(func):
		# type: (Callable, ) -> Callable

		@wraps(func)
		def inner(*args, **kwargs):
			# type: (*Any, **Any) -> Any

			if not ignoreargs:
				if keyfunc is None:
					hash = key_to_hash(args_to_key(args, kwargs), protocol=protocol)
				else:
					hash = keyfunc(args, kwargs)
				fullpath = path / hash
			else:
				if args or kwargs:
					logger.warning("cache file decorator for %s called with arguments", func.__name__)
				fullpath = fspath(path).format(ppv=protocol)

			try:
				invalid = now() - mdatetime(fullpath) > _duration
			except FileNotFoundError:
				invalid = True

			if invalid:
				if not ignoreargs:
					path.mkdir(parents=True, exist_ok=True)

				if generator and not consume:
					it = func(*args, **kwargs)
					logger.info("Writing iterable to cache: %s", fullpath)
					return write_iter(it, fullpath, protocol=protocol, safe=True)
				else:
					with context("Result calculated in {delta} seconds"):
						if generator and consume:
							result = list(func(*args, **kwargs))
						else:
							result = func(*args, **kwargs)
					write_pickle(result, fullpath, protocol=protocol, safe=True)
					return result
			else:
				if generator and not consume:
					logger.info("Loading iterable from cache: %s", fullpath)
					return read_iter(fullpath)
				else:
					with context("Result loaded from cache in {delta} seconds"):
						return read_pickle(fullpath)
		return inner

	return decorator
