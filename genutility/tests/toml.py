from __future__ import absolute_import, division, print_function, unicode_literals

from future.utils import PY2
from unittest import skipIf

from genutility.test import MyTestCase, parametrize, closeable_tempfile
from genutility.toml import read_toml, write_toml

class TomlTest(MyTestCase):

	@parametrize(
		("", {}),
		("asd = 1\n", {"asd": 1}),
	)
	def test_read_toml(self, content, truth):
		with closeable_tempfile(mode="wt", encoding="utf-8") as (f, fname):
			f.write(content)
			f.flush() # or f.close()
			result = read_toml(fname)

		self.assertEqual(truth, result)

	@skipIf(PY2, "toml.dumps returns inconsistent string types on Python 2")
	@parametrize(
		({}, ""),
		({"asd": 1}, "asd = 1\n")
	)
	def test_write_toml(self, content, truth):
		with closeable_tempfile(mode="w+t", encoding="utf-8") as (f, fname):
			write_toml(content, fname)
			result = f.read()

		self.assertEqual(truth, result)

if __name__ == "__main__":
	import unittest
	unittest.main()
