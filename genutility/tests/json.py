from __future__ import absolute_import, division, print_function, unicode_literals

from io import StringIO
from genutility.test import MyTestCase, parametrize, closeable_tempfile
from genutility.json import json_lines, read_json_lines

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

	@parametrize(
		('', tuple()),
		('{"asd": 1}\n["asd", 1]\n', ({"asd": 1}, ["asd", 1]))
	)
	def test_read_json_lines(self, content, truth):
		with closeable_tempfile(mode="wt", encoding="utf-8") as (f, fname):
			f.write(content)
			f.close() # Windows compatibility, otherwise sharing violation
			result = tuple(read_json_lines(fname))

		self.assertEqual(truth, result)

if __name__ == "__main__":
	import unittest
	unittest.main()
