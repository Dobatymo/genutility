from __future__ import absolute_import, division, print_function, unicode_literals

import unittest, os.path, sys
from genutility.test import MyTestCase, parametrize
from genutility.pdf import join_pdfs_in_folder
from genutility.compat.pathlib import Path

class PdfTest(MyTestCase):

	@unittest.skipIf(sys.version_info < (3, 6), "pdf key order is random")
	@parametrize(
		("testfiles/pdf/", "testtemp/joined.pdf", "testfiles/joined.pdf"),
	)
	def test_join_pdfs_in_folder(self, path, out, truth):
		with self.assertNoRaise():
			join_pdfs_in_folder(Path(path), out, overwrite=True)

		self.assertFilesEqual(out, truth)

if __name__ == "__main__":
	import unittest
	unittest.main()
