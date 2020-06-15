from __future__ import absolute_import, division, print_function, unicode_literals

from ctypes import sizeof

from genutility.test import MyTestCase
from genutility.win.device import EMPTY_BUFFER


class DeviceTest(MyTestCase):

	def test_empty_buffer(self):
		self.assertEqual(0, sizeof(EMPTY_BUFFER))


if __name__ == "__main__":
	import unittest
	unittest.main()
