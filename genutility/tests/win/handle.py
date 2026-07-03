import sys
from unittest import skipIf

from genutility.test import MyTestCase


@skipIf(sys.platform != "win32", "Windows only")
class WindowsHandleTest(MyTestCase):
    def test_overlapped(self):
        from genutility.win.handle import WindowsHandle

        self.assertFalse(WindowsHandle(1).overlapped)
        self.assertTrue(WindowsHandle(1, timeout_ms=1).overlapped)

    def test_handle_type(self):
        from genutility.win.handle import WindowsHandle

        with self.assertRaises(TypeError):
            WindowsHandle("1")


if __name__ == "__main__":
    import unittest

    unittest.main()
