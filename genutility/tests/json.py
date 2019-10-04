from __future__ import absolute_import, division, print_function, unicode_literals

from io import StringIO

from genutility.test import MyTestCase, parametrize
from genutility.json import json_lines

class JsonTest(MyTestCase):

	@parametrize(
		('', tuple()),
		('{"asd": 1}\n["asd", 1]\n', ({"asd": 1}, ["asd", 1]))
	)
	def test_json_lines_from_stream(self, content, truth):
		stream = StringIO(content)
		with json_lines.from_stream(stream) as fr:
			result = tuple(fr)

		self.assertEqual(truth, result)

if __name__ == "__main__":
	import unittest
	unittest.main()
