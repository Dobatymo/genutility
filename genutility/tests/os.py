from __future__ import absolute_import, division, print_function, unicode_literals

from time import sleep
from genutility.test import MyTestCase
from genutility.os import interrupt

class TestOS(MyTestCase):

	def test_interrupt(self):
		with self.assertRaises(KeyboardInterrupt):
			interrupt()
			sleep(1)

if __name__ == "__main__":
	import unittest
	unittest.main()
