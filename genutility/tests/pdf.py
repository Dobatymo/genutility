from __future__ import absolute_import, division, print_function, unicode_literals

import os.path
from genutility.test import MyTestCase, parametrize
from genutility.pdf import join_pdfs_in_folder

class PdfTest(MyTestCase):

	@parametrize(
		("testfiles/pdf/", "testtemp/joined.pdf", "testfiles/joined.pdf"),
	)
	def test_join_pdfs_in_folder(self, path, out, truth):
		with self.assertNoRaise():
			join_pdfs_in_folder(path, out, overwrite=True)
		self.assertFilesEqual(out, truth)

if __name__ == "__main__":
	import unittest
	unittest.main()
