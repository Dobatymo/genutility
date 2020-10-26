from __future__ import generator_stop

from ctypes import sizeof

from genutility.hardware.ata import IDENTIFY_DEVICE_DATA
from genutility.test import MyTestCase


class AtaTest(MyTestCase):

	def test_empty_buffer(self):
		self.assertEqual(512, sizeof(IDENTIFY_DEVICE_DATA()))


if __name__ == "__main__":
	import unittest
	unittest.main()
