from __future__ import generator_stop

from genutility._files import to_dos_device_path, to_dos_path
from genutility.test import MyTestCase, parametrize


class _FilesTest(MyTestCase):
    @parametrize(
        ("", ""),
        ("C:\\asd", "\\\\?\\C:\\asd"),
        ("C:/asd", "\\\\?\\C:/asd"),
        ("\\\\?\\C:\\asd", "\\\\?\\C:\\asd"),
        ("\\\\?\\C:/asd", "\\\\?\\C:/asd"),
        ("\\\\server\\share", "\\\\?\\UNC\\server\\share"),
        ("\\\\server/share", "\\\\?\\UNC\\server/share"),
        ("\\\\?\\UNC\\server\\share", "\\\\?\\UNC\\server\\share"),
        ("\\\\?\\UNC\\server/share", "\\\\?\\UNC\\server/share"),
    )
    def test_to_dos_device_path(self, path, truth):
        result = to_dos_device_path(path)
        self.assertEqual(truth, result)

    @parametrize(
        ("", ""),
        ("C:\\asd", "C:\\asd"),
        ("C:/asd", "C:/asd"),
        ("\\\\server\\share", "\\\\server\\share"),
        ("\\\\server/share", "\\\\server/share"),
        ("\\\\?\\C:\\asd", "C:\\asd"),
        ("\\\\?\\C:/asd", "C:/asd"),
        ("\\\\?\\UNC\\server\\share", "\\\\server\\share"),
        ("\\\\?\\UNC\\server/share", "\\\\server/share"),
    )
    def test_to_dos_path(self, path, truth):
        result = to_dos_path(path)
        self.assertEqual(truth, result)


if __name__ == "__main__":
    import unittest

    unittest.main()
