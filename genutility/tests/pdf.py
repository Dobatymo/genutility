from pathlib import Path
from unittest import skipIf

from importlib_metadata import version as get_version
from packaging.version import Version

from genutility.pdf import iter_pdf_text, join_pdfs_in_folder
from genutility.test import MyTestCase, parametrize, print_file_diff

OLD_PYPDF = Version(get_version("pypdf")) < Version("5.0.0")


class PdfTest(MyTestCase):
    @skipIf(OLD_PYPDF, "pypdf<5.0.0")
    @parametrize(
        ("testfiles/pdf/", "testtemp/joined.pdf", "testfiles/joined.pdf"),
    )
    def test_join_pdfs_in_folder(self, path, out, truth):
        with self.assertNoRaise():
            join_pdfs_in_folder(Path(path), out, overwrite=True)

        try:
            self.assertFilesEqual(out, truth)
        except AssertionError:
            print_file_diff(truth, out, encoding="latin1")
            raise

    def test_iter_pdf_text(self):
        truth = ["Hello World", "HELLO WORLD"]
        result = iter_pdf_text("testfiles/joined.pdf")

        self.assertIterEqual(truth, result)


if __name__ == "__main__":
    import unittest

    unittest.main()
