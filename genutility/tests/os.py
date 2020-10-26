from __future__ import generator_stop

from time import sleep

from genutility.os import interrupt
from genutility.test import MyTestCase


class TestOS(MyTestCase):

	def test_interrupt(self):
		with self.assertRaises(KeyboardInterrupt):
			interrupt()
			sleep(1)

if __name__ == "__main__":
	import unittest
	unittest.main()
