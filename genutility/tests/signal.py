from __future__ import absolute_import, division, print_function, unicode_literals

import os, time, errno

try:
	from unittest.mock import Mock
except ImportError:
	from mock import Mock # type: ignore # backport

from genutility.test import MyTestCase
from genutility.os import interrupt
from genutility.signal import HandleKeyboardInterrupt

class SignalTest(MyTestCase):

	def __init__(self, *args, **kwargs):
		MyTestCase.__init__(self, *args, **kwargs)

	@staticmethod
	def busywait(): # only works with python 3 (3.5+?)
		for i in range(10):
			time.sleep(0.1)

	@staticmethod
	def busywait_no_eintr():
		""" sleep can raise 'IOError: [Errno 4] Interrupted function call'
			on python 2.7 on signal
		"""

		try:
			for i in range(10):
				time.sleep(0.1)
		except IOError as e: #
			if e.errno == errno.EINTR: # 4
				pass
			else:
				raise

	def call(self, raise_after, a, b, c, d):
		try:
			with HandleKeyboardInterrupt(raise_after):
				try:
					a()
					interrupt()
					self.busywait_no_eintr()
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
			self.busywait_no_eintr()
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
