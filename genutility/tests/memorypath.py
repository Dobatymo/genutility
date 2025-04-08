import stat

from genutility.memorypath import MemoryPath, StatResult
from genutility.test import MyTestCase


class MemoryPathTest(MyTestCase):
    """MemoryPath is currently tested more extensively in `sqlitefspath`."""

    def test_file_exists(self):
        p = MemoryPath()
        self.assertEqual(False, p.exists())
        self.assertEqual(False, p.is_file())
        self.assertEqual(False, p.is_dir())

        with self.assertRaises(FileNotFoundError):
            p.read_bytes()
        with self.assertRaises(FileNotFoundError):
            p.stat()

    def test_dir_exists(self):
        p = MemoryPath(children=[])
        self.assertEqual(True, p.exists())
        self.assertEqual(False, p.is_file())
        self.assertEqual(True, p.is_dir())

        with self.assertRaises(IsADirectoryError):
            p.read_bytes()

        self.assertEqual(StatResult(st_mode=stat.S_IFDIR, st_ino=id(p)), p.stat())


if __name__ == "__main__":
    import unittest

    unittest.main()
