from __future__ import generator_stop

from datetime import time, timezone

from genutility.compat.datetime import datetime
from genutility.datetime import between, datetime_from_utc_timestamp, now
from genutility.test import MyTestCase, parametrize


class DatetimeTest(MyTestCase):

	def test_now_isoformat(self):
		dt = now()
		isostr = dt.isoformat()
		dt2 = datetime.fromisoformat(isostr)
		self.assertEqual(dt, dt2)

	@parametrize(
		(0, datetime(1970, 1, 1, 0, 0, tzinfo=timezone.utc))
	)
	def test_datetime_from_utc_timestamp(self, input, truth):
		result = datetime_from_utc_timestamp(input)
		self.assertEqual(result, truth)

	@parametrize(
		(time(12), time(11), time(13), True),
		(time(12), time(13), time(11), False),
		(time(12), time(15), time(13), True),
		(time(12), time(13), time(15), False),
		(time(12), time(11), time(9), True),
		(time(12), time(9), time(11), False),

		(time(11), time(11), time(13), True),
		(time(13), time(11), time(13), True),
		(time(15), time(15), time(13), True),
		(time(13), time(15), time(13), True),
		(time(13), time(0), time(0), True),

		(datetime(1970, 1, 2, tzinfo=timezone.utc), datetime(1970, 1, 1, tzinfo=timezone.utc), datetime(1970, 1, 3, tzinfo=timezone.utc), True),
		(datetime(1970, 1, 2, tzinfo=timezone.utc), datetime(1970, 1, 1, tzinfo=timezone.utc), None, True),
		(datetime(1970, 1, 2, tzinfo=timezone.utc), None, datetime(1970, 1, 3, tzinfo=timezone.utc), True),
		(datetime(1970, 1, 3, tzinfo=timezone.utc), datetime(1970, 1, 1, tzinfo=timezone.utc), datetime(1970, 1, 2, tzinfo=timezone.utc), False),
		(datetime(1970, 1, 1, tzinfo=timezone.utc), datetime(1970, 1, 2, tzinfo=timezone.utc), None, False),
		(datetime(1970, 1, 3, tzinfo=timezone.utc), None, datetime(1970, 1, 2, tzinfo=timezone.utc), False),
	)
	def test_between(self, dt, start, end, truth):
		result = between(dt, start, end)
		self.assertEqual(result, truth)

if __name__ == "__main__":
	import unittest
	unittest.main()
