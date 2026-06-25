import os
from pathlib import Path

from genutility.filesystem import scandir_rec
from genutility.test import MyTestCase, parametrize


class SymlinkTests(MyTestCase):

    def setUp(self):
        self.test_root = Path("test_symlinks")
        self.test_root.mkdir(exist_ok=True)

        # Set up directories and files
        (self.test_root / "dir").mkdir(exist_ok=True)
        (self.test_root / "dir" / "file.txt").write_text("content")

        # Create symlink
        if os.name == "nt":
            os.system(f'mklink /D "{self.test_root / "dir-symlink"}" "{self.test_root / "dir"}"')
        else:
            (self.test_root / "dir-symlink").symlink_to(self.test_root / "dir")

    def tearDown(self):
        for item in self.test_root.rglob("*"):
            if item.is_symlink() or item.is_file():
                item.unlink()
            elif item.is_dir():
                item.rmdir()
        self.test_root.rmdir()

    def test_symlink_prevent_loops(self):
        """Test scandir_rec with prevent_loops=True to ensure symlinks are handled correctly."""
        results = scandir_rec(self.test_root, rec=True, prevent_loops=True, files=True, dirs=True)
        entries = [entry.name for entry in results]

        expected_entries = [
            "dir",
            "dir-symlink",
            "file.txt",
        ]
        self.assertUnorderedSeqEqual(entries, expected_entries)

    def test_symlink_allow_loops(self):
        """Test scandir_rec with prevent_loops=False to see if infinite loops are avoided and duplicate entries appear."""
        results = scandir_rec(self.test_root, rec=True, prevent_loops=False, files=True, dirs=True)
        entries = [entry.name for entry in results]

        # With prevent_loops=False, duplicates may appear
        expected_entries = [
            "dir",
            "dir-symlink",
            "file.txt",
            "file.txt",  # Duplicate if symlink traversed recursively
        ]
        self.assertUnorderedSeqEqual(entries, expected_entries)


if __name__ == "__main__":
    import unittest

    unittest.main()
