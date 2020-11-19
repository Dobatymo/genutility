from __future__ import generator_stop

import sys
from ctypes import sizeof
from unittest import SkipTest

if sys.platform != "win32":
	raise SkipTest("win submodule only available on Windows")

from genutility.test import MyTestCase
from genutility.win.device import EMPTY_BUFFER


class DeviceTest(MyTestCase):

	def test_empty_buffer(self):
		self.assertEqual(0, sizeof(EMPTY_BUFFER))

if __name__ == "__main__":
	import unittest
	unittest.main()
