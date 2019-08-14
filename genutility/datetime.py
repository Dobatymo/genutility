from __future__ import absolute_import, division, print_function, unicode_literals

from .compat.datetime import datetime, timezone

def now():
	# type: () -> datetime

	""" Returns the current datetime as timezone aware object in UTC timezone. """

	return datetime.now(timezone.utc)
