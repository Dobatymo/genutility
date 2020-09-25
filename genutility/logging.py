from logging import Formatter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from logging import LogRecord
	from typing import Any, Dict

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
