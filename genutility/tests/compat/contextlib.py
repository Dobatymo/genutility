from __future__ import absolute_import, division, print_function, unicode_literals

from genutility.test import MyTestCase
from genutility.compat.contextlib import nullcontext

class ContextTest(MyTestCase):

	def test_nullcontext(self):
		with nullcontext():
			pass

		val = 1337
		with nullcontext(val) as res:
			self.assertEqual(res, val)

if __name__ == "__main__":
	import unittest
	unittest.main()
