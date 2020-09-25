from __future__ import absolute_import, division, print_function, unicode_literals

from genutility.filesystem import append_to_filename
from genutility.test import MyTestCase, parametrize


class FilesystemTest(MyTestCase):

	@parametrize(
		("qwe.zxc", ".xxx", "qwe.xxx.zxc"),
		("asd/qwe.zxc", ".xxx", "asd/qwe.xxx.zxc"),
		(".asd", ".xxx", ".asd.xxx"),
		("asd/.qwe", ".xxx", "asd/.qwe.xxx"),
		("asd/", ".xxx", "asd/.xxx"), # Not a file. Should maybe be handled differently...
	)
	def test_append_to_filename(self, path, s, truth):
		result = append_to_filename(path, s)
		self.assertEqual(truth, result)

if __name__ == "__main__":
	import unittest
	unittest.main()
