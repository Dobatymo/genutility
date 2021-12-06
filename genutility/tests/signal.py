from __future__ import generator_stop

import time
from unittest.mock import Mock

from genutility.os import interrupt
from genutility.signal import HandleKeyboardInterrupt
from genutility.test import MyTestCase


class SignalTest(MyTestCase):

	def __init__(self, *args, **kwargs):
		MyTestCase.__init__(self, *args, **kwargs)

	@staticmethod
	def busywait():
		for i in range(10):
			time.sleep(0.1)

	def call(self, raise_after, a, b, c, d):
		try:
			with HandleKeyboardInterrupt(raise_after):
				try:
					a()
					interrupt()
					self.busywait()
					b()
				except KeyboardInterrupt:
					c()
		except KeyboardInterrupt:
			d()

	def test_signal_test(self):
		a = Mock()
		b = Mock()
		c = Mock()
		try:
			a()
			interrupt()
			self.busywait()
			b()
		except KeyboardInterrupt:
			c()
		a.assert_called_with()
		b.assert_not_called()
		c.assert_called_with()

	def test_raise_after_true(self):
		a = Mock()
		b = Mock()
		c = Mock()
		d = Mock()
		self.call(True, a, b, c, d)
		a.assert_called_with()
		b.assert_called_with()
		c.assert_not_called()
		d.assert_called_with()

	def test_raise_after_false(self):
		a = Mock()
		b = Mock()
		c = Mock()
		d = Mock()
		self.call(False, a, b, c, d)
		a.assert_called_with()
		b.assert_called_with()
		c.assert_not_called()
		d.assert_not_called()

if __name__ == "__main__":
	import unittest
	unittest.main()
