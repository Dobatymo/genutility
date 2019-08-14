from __future__ import absolute_import, division, print_function, unicode_literals

import os.path
from genutility.test import MyTestCase, parametrize
from genutility.pdf import join_pdfs_in_folder

class PdfTest(MyTestCase):

	@parametrize(
		("testfiles/pdf/", "testfiles/out/joined.pdf"),
	)
	def test_join_pdfs_in_folder(self, path, out):
		with self.assertNoRaise():
			join_pdfs_in_folder(path, out)
		self.assertGreater(os.path.getsize(out), 10*1024)

if __name__ == "__main__":
	import unittest
	unittest.main()
