from __future__ import absolute_import, division, print_function, unicode_literals

import sys
import unittest

from genutility.compat.pathlib import Path
from genutility.pdf import join_pdfs_in_folder
from genutility.test import MyTestCase, parametrize

LESSTHANPY36 = sys.version_info < (3, 6)

class PdfTest(MyTestCase):

	@unittest.skipIf(LESSTHANPY36, "pdf key order is random")
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
