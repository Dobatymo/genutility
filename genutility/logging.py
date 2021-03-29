from __future__ import generator_stop

from logging import Formatter
from typing import TYPE_CHECKING

from .datetime import datetime_from_utc_timestamp

if TYPE_CHECKING:
	from logging import LogRecord
	from typing import Any, Dict, Optional

class IsoDatetimeFormatter(Formatter):

	""" Displays the time in ISO 8601 format.
		Instead of passing a formatting string to `datefmt` in the initializer, `sep` and `timespec`
		(see `datetime.datetime.isoformat`) as well as `aslocal` (see genutility.datetime.datetime_from_utc_timestamp`)
		can be passed.
	"""

	def __init__(self, fmt=None, datefmt=None, style='%', validate=True, sep='T', timespec='auto', aslocal=False):
		# type: (Optional[str], None, str, bool, str, str, bool) -> None

		Formatter.__init__(self, fmt, datefmt, style, validate)
		assert datefmt is None
		self.sep = sep
		self.timespec = timespec
		self.aslocal = aslocal

	def formatTime(self, record, datefmt):
		# type: (LogRecord, None) -> str

		return datetime_from_utc_timestamp(record.created, aslocal=self.aslocal).isoformat(self.sep, self.timespec)

class OverwriteFormatter(Formatter):

	""" Usually the default Formatter disallows overwriting of built-in fields
		like filename, funcName, lineno and so on. Here you can specify a mapping
		to set these values anyway.

		Example:
			formatter = OverwriteFormatter({"func_name": "funcName"}, "%(funcName)s: %(message)s")
			and then pass `extra={"func_name": "thename"}` to the logging calls.
			If the the custom fields are not passed, the original values will be used.
	"""

	def __init__(self, map, *args, **kwargs):
		# type: (Dict[str, str], *Any, **Any) -> None

		self.map = map
		Formatter.__init__(self, *args, **kwargs)

	def format(self, record):
		# type: (LogRecord, ) -> str

		for k, v in self.map.items():
			try:
				setattr(record, v, getattr(record, k))
			except AttributeError:
				pass

		return Formatter.format(self, record)

if __name__ == "__main__":
	import logging

	logger = logging.getLogger(__name__)
	handler = logging.StreamHandler()
	formatter = OverwriteFormatter({"func_name": "funcName"}, "%(funcName)s: %(message)s")
	handler.setFormatter(formatter)
	logger.addHandler(handler)

	logger.warning("asd")
	logger.warning("asd", extra={"func_name": "thename"})
