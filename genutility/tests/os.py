import sys
from time import sleep
from unittest import skipIf

from genutility.os import interrupt
from genutility.test import MyTestCase


class TestOS(MyTestCase):
    @skipIf(sys.platform == "win32", "test might interrupt subsequent tests on windows")
    def test_interrupt(self):
        with self.assertRaises(KeyboardInterrupt):
            interrupt()
            sleep(1)


if __name__ == "__main__":
    import unittest

    unittest.main()
