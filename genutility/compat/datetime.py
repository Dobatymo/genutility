from __future__ import absolute_import, division, print_function, unicode_literals

from datetime import datetime as _datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from typing import Optional

try:
	from datetime import timezone

except ImportError:

	from datetime import timedelta, tzinfo

	class timezone(tzinfo):

		def __init__(self, offset, name=None):
			# type: (int, Optional[str]) -> None

			self.offset = offset
			self.name = name

		def __reduce__(self):
			return (timezone, (self.offset, self.name))

		def utcoffset(self, dt):
			return self.offset

		def dst(self, dt):
			return timedelta(0)

		def tzname(self, dt):
			if self.name:
				return self.name
			else:
				raise NotImplementedError

	timezone.utc = timezone(timedelta(0))

try:
	_datetime.fromisoformat
	datetime = _datetime

except AttributeError:

	import re
	from datetime import timedelta

	from ..string import tryint

	isoformatre = re.compile(r"^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2}):(\d{2})\.(\d{6})(\+|-)(\d{2}):(\d{2})$")
	isoformatre2 = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")

	class datetime(_datetime):

		@classmethod
		def fromisoformat(cls, date_string):
			# (str, ) -> datetime

			""" Converts an ISO 8601 date and time with timezone string to a timezone aware datetime.
				eg. '2019-03-01T11:30:01.123000+00:00'
				eg. '2019-02-02T12:30:02.456000+04:00'
				eg. '2019-01-03T22:30:03.789000-07:00'
			"""

			try:
				groups = isoformatre.match(date_string).groups()
				year, month, day, hour, minute, second, milliseconds, tzsign, tzhours, tzminutes = map(tryint, groups)
			except AttributeError:
				groups = isoformatre2.match(date_string).groups()
				year, month, day = map(tryint, groups)
				hour, minute, second, milliseconds, tzsign, tzhours, tzminutes = (0, 0, 0, 0, "+", 0, 0)

			offset = timedelta(hours=tzhours, minutes=tzminutes)

			if tzsign == "-":
				offset = -offset

			return cls(year, month, day, hour, minute, second, milliseconds, tzinfo=timezone(offset))
