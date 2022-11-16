from __future__ import generator_stop

import os.path
from pathlib import Path
from types import TracebackType
from typing import Optional, Type

from genutility.filesystem import append_to_filename, scandir_rec
from genutility.test import MyTestCase, parametrize


class HandleSymlinkErrors:
    def __init__(self, testcase: MyTestCase) -> None:
        self.testcase = testcase

    def __enter__(self) -> None:
        pass

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> Optional[bool]:
        if isinstance(exc_value, FileExistsError):
            return True
        elif isinstance(exc_value, OSError):
            if getattr(exc_value, "winerror", 0) == 1314:
                self.testcase.skipTest("Creating symlinks requires admin permissions on Windows")

        return False


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

    def test_scandir_rec_links(self):
        base = Path("testtemp/scandir")
        base.mkdir(parents=False, exist_ok=True)

        (base / "dir").mkdir(exist_ok=True)
        (base / "dir" / "file.ext").touch()
        with HandleSymlinkErrors(self):
            (base / "dir-symlink").symlink_to("dir")
        with HandleSymlinkErrors(self):
            (base / "file-symlink.ext").symlink_to(
                os.path.join("dir", "file.ext")
            )  # note: correct pathsep is really important here

        truth = ["dir", "dir-symlink", "file-symlink.ext", "file.ext"]
        results = list(entry.name for entry in scandir_rec(base, rec=True, files=True, dirs=True, prevent_loops=True))
        self.assertUnorderedSeqEqual(truth, results)

        truth = ["dir", "dir-symlink", "file-symlink.ext", "file.ext", "file.ext"]
        results = list(entry.name for entry in scandir_rec(base, rec=True, files=True, dirs=True, prevent_loops=False))
        self.assertUnorderedSeqEqual(truth, results)


if __name__ == "__main__":
    import unittest

    unittest.main()
