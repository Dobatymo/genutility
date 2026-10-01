import sys

from genutility.exceptions import reraise
from genutility.test import MyTestCase


class ExceptionsTest(MyTestCase):
    def test_reraise(self):
        try:
            raise ValueError("test")
        except ValueError:
            exc_info = sys.exc_info()

        with self.assertRaisesRegex(ValueError, "test"):
            reraise(exc_info)


if __name__ == "__main__":
    import unittest

    unittest.main()
