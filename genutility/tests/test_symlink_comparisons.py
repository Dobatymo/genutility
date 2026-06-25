import os
from pathlib import Path

from genutility.filesystem import clean_directory_by_extension, equal_dirs, search
from genutility.test import MyTestCase


class SymlinkComparisonTests(MyTestCase):

    def setUp(self):
        self.test_root = Path("test_symlink_comparisons")
        self.test_root.mkdir(exist_ok=True)

        # Create directories and files
        (self.test_root / "dir1").mkdir(exist_ok=True)
        (self.test_root / "dir1" / "file.txt").write_text("content1")

        (self.test_root / "dir2").mkdir(exist_ok=True)
        (self.test_root / "dir2" / "file.txt").write_text("content1")

        # Create symlinks
        (self.test_root / "dir1" / "symlink-to-file").symlink_to(self.test_root / "dir1" / "file.txt")
        (self.test_root / "dir2" / "symlink-to-file").symlink_to(self.test_root / "dir2" / "file.txt")

    def tearDown(self):
        for item in self.test_root.rglob("*"):
            if item.is_symlink() or item.is_file():
                item.unlink()
            elif item.is_dir():
                item.rmdir()
        self.test_root.rmdir()

    def test_equal_dirs_with_symlinks(self):
        """Test if equal_dirs considers symlinked files correctly."""
        result = equal_dirs(self.test_root / "dir1", self.test_root / "dir2")
        self.assertFalse(result, "Directories with symlinks should not be considered equal by default")

    def test_search_with_symlinks(self):
        """Test if search respects symlinked files."""
        results = list(search([self.test_root / "dir1"], pattern="*.txt"))
        self.assertIn("file.txt", [entry.name for entry in results])  # Should include the actual file
        self.assertIn("symlink-to-file", [entry.name for entry in results])  # Should include the symlink

    def test_clean_directory_by_extension_with_symlinks(self):
        """Test if clean_directory_by_extension respects symlinks."""
        # Add .bak files
        (self.test_root / "dir1" / "file.txt.bak").write_text("backup")
        (self.test_root / "dir2" / "file.txt.bak").symlink_to(self.test_root / "dir2" / "file.txt")

        clean_directory_by_extension(self.test_root / "dir1", ext=".bak")
        self.assertFalse((self.test_root / "dir1" / "file.txt.bak").exists(), "Backup file should be cleaned")

        clean_directory_by_extension(self.test_root / "dir2", ext=".bak")
        # The symlink pointing to a .bak file may or may not be cleaned depending on implementation
        self.assertTrue(
            (self.test_root / "dir2" / "file.txt.bak").exists(), "Symlinked backup file behavior not defined"
        )


if __name__ == "__main__":
    import unittest

    unittest.main()
