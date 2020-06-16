from __future__ import absolute_import, division, print_function, unicode_literals

from ctypes import sizeof

from genutility.test import MyTestCase
from genutility.hardware.ata import IDENTIFY_DEVICE_DATA

class AtaTest(MyTestCase):

	def test_empty_buffer(self):
		self.assertEqual(512, sizeof(IDENTIFY_DEVICE_DATA()))


if __name__ == "__main__":
	import unittest
	unittest.main()
