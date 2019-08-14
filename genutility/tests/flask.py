from __future__ import absolute_import, division, print_function, unicode_literals

from genutility.test import MyTestCase, parametrize
from genutility.flask import Base64Converter

class FlaskTest(MyTestCase):

	@parametrize(
		("你好", "5L2g5aW9"),
	)
	def test_Base64Converter(self, python, url):
		c = Base64Converter({})

		result = c.to_url(python)
		self.assertEqual(url, result)

		result = c.to_python(result)
		self.assertEqual(python, result)

if __name__ == '__main__':
	import unittest
	unittest.main()
