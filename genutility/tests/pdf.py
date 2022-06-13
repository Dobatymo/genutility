from __future__ import generator_stop

from pathlib import Path

from genutility.pdf import iter_pdf_text, join_pdfs_in_folder
from genutility.test import MyTestCase, parametrize


class PdfTest(MyTestCase):
    @parametrize(
        ("testfiles/pdf/", "testtemp/joined.pdf", "testfiles/joined.pdf"),
    )
    def test_join_pdfs_in_folder(self, path, out, truth):
        with self.assertNoRaise():
            join_pdfs_in_folder(Path(path), out, overwrite=True)

        self.assertFilesEqual(out, truth)

    def test_iter_pdf_text(self):
        truth = ["Hello World", "Hello World"]
        result = iter_pdf_text("testfiles/joined.pdf")

        self.assertIterEqual(truth, result)


if __name__ == "__main__":
    import unittest

    unittest.main()
