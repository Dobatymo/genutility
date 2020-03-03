from __future__ import absolute_import, division, print_function, unicode_literals

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
