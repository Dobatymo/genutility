from __future__ import absolute_import, division, print_function, unicode_literals

from genutility.compat.datetime import datetime, timezone
from genutility.datetime import datetime_from_utc_timestamp, now
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

if __name__ == "__main__":
	import unittest
	unittest.main()
