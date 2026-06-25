from genutility.test import MyTestCase
from genutility.win.handle import WindowsHandle


class WindowsHandleTest(MyTestCase):
    def test_overlapped(self):
        self.assertFalse(WindowsHandle(1).overlapped)
        self.assertTrue(WindowsHandle(1, timeout_ms=1).overlapped)

    def test_handle_type(self):
        with self.assertRaises(TypeError):
            WindowsHandle("1")


if __name__ == "__main__":
    import unittest

    unittest.main()
