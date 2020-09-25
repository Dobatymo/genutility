from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import time
from datetime import timedelta, tzinfo

from .compat.datetime import datetime, timezone

utcmin = datetime.min.replace(tzinfo=timezone.utc)
utcmax = datetime.max.replace(tzinfo=timezone.utc)

def now(aslocal=False):
	# type: (bool, ) -> datetime

	""" Returns the current datetime as timezone aware object in
		UTC timezone if `aslocal=False` (the default)
		or local timezone if `aslocal=True`.
	"""

	dt = datetime.now(timezone.utc)
	if aslocal:
		dt = dt.astimezone(None)
	return dt

def datetime_from_utc_timestamp(epoch, aslocal=False):
	# type: (int, bool) -> datetime

	""" Converts a UNIX epoch time in seconds to a timezone aware datetime. """

	dt = datetime.fromtimestamp(epoch, timezone.utc)
	if aslocal:
		dt = dt.astimezone(None)
	return dt

def datetime_from_utc_timestamp_ns(epoch, aslocal=False):
	# type: (int, bool) -> datetime

	""" Converts a UNIX epoch time in nano seconds to a timezone aware datetime. """

	seconds, ns = divmod(epoch, 1000000000)

	dt = datetime.fromtimestamp(seconds, timezone.utc)
	dt.microsecond = ns // 1000

	if aslocal:
		dt = dt.astimezone(None)

	return dt

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

# deprecated
def localnow():
	# type: () -> datetime

	""" Returns the current datetime as timezone aware object in local timezone. """

	return datetime.now(localtimezone)
