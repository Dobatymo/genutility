from __future__ import absolute_import, division, print_function, unicode_literals

from genutility.test import MyTestCase
from genutility.datetime import now
from genutility.compat.datetime import datetime

class DatetimeTest(MyTestCase):

	def test_now_isoformat(self):
		dt = now()
		isostr = dt.isoformat()
		dt2 = datetime.fromisoformat(isostr)
		self.assertEqual(dt, dt2)

if __name__ == "__main__":
	import unittest
	unittest.main()
