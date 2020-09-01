from __future__ import absolute_import, division, print_function, unicode_literals

import logging, json
from io import StringIO
from genutility.test import MyTestCase, parametrize, closeable_tempfile
from genutility.json import json_lines, read_json_lines, JsonLinesFormatter

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

	def test_JsonLinesFormatter(self):

		stream = StringIO()

		logger = logging.getLogger("JsonLinesFormatter")
		logger.setLevel(logging.INFO)
		handler = logging.StreamHandler(stream)
		handler.setLevel(logging.INFO)
		jl_formatter = JsonLinesFormatter(include={"datetime-str"}, builtins={"thread"})
		handler.setFormatter(jl_formatter)
		logger.addHandler(handler)

		logger.info({"key": "test"})
		d = json.loads(stream.getvalue())

		self.assertEqual(d["key"], "test")
		self.assertIn("datetime-str", d)
		self.assertIn("thread", d)

if __name__ == "__main__":
	import unittest
	unittest.main()
