from __future__ import absolute_import, division, print_function, unicode_literals

import logging, time
from datetime import tzinfo, timedelta

from .compat.datetime import datetime, timezone

utcmin = datetime.min.replace(tzinfo=timezone.utc)
utcmax = datetime.max.replace(tzinfo=timezone.utc)

def now():
	# type: () -> datetime

	""" Returns the current datetime as timezone aware object in UTC timezone. """

	return datetime.now(timezone.utc)

# was: datetime_from_utc_timestamp
def datetime_from_utc_timestamp(epoch):
	# type: (int, ) -> datetime

	""" Converts a UNIX epoch time to a timezone aware datetime. """

	return datetime.fromtimestamp(epoch, timezone.utc)

class LocalTimezone(tzinfo):

	def __init__(self):
		if time.daylight:
			self.daylight = timedelta(seconds=-time.altzone) - timedelta(seconds=-time.timezone)
			self.offset = timedelta(seconds=-time.altzone)
			self.name = time.tzname[1]
		else:
			self.daylight = timedelta(0)
			self.offset = timedelta(seconds=-time.timezone)
			self.name = time.tzname[0]

	def dst(self, dt):
		return self.daylight

	def utcoffset(self, dt):
		return self.offset

	def tzname(self):
		return self.name

	def __repr__(self):
		return "genutility.datetime.localtimezone"

localtimezone = LocalTimezone()

def localnow():
	# type: () -> datetime

	""" Returns the current datetime as timezone aware object in local timezone. """

	return datetime.now(localtimezone)
