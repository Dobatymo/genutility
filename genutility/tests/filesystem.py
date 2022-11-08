from __future__ import generator_stop

from genutility.filesystem import append_to_filename, scandir_rec
from genutility.test import MyTestCase, parametrize


class FilesystemTest(MyTestCase):
    @parametrize(
        ("qwe.zxc", ".xxx", "qwe.xxx.zxc"),
        ("asd/qwe.zxc", ".xxx", "asd/qwe.xxx.zxc"),
        (".asd", ".xxx", ".asd.xxx"),
        ("asd/.qwe", ".xxx", "asd/.qwe.xxx"),
        ("asd/", ".xxx", "asd/.xxx"),  # Not a file. Should maybe be handled differently...
    )
    def test_append_to_filename(self, path, s, truth):
        result = append_to_filename(path, s)
        self.assertEqual(truth, result)

    def test_scandir_rec(self):
        base = ["joined.pdf", "quadrant-0.png", "quadrant-1.png", "quadrant-2.png", "quadrant-3.png"]
        rec = [
            "01.txt",
            "02.txt",
            "03.txt",
            "04.txt",
            "06.txt",
            "08.txt",
            "10.txt",
            "13.txt",
            "16.txt",
            "minimal_1.pdf",
            "minimal_2.pdf",
        ]

        results = list(entry.name for entry in scandir_rec("testfiles", rec=True))
        self.assertUnorderedSeqEqual(base + rec, results)

        results = list(entry.name for entry in scandir_rec("testfiles", rec=False))
        self.assertUnorderedSeqEqual(base, results)


if __name__ == "__main__":
    import unittest

    unittest.main()
