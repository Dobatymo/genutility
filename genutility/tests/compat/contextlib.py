from __future__ import generator_stop

from genutility.compat.contextlib import nullcontext
from genutility.test import MyTestCase


class ContextTest(MyTestCase):
    def test_nullcontext(self):
        with nullcontext():
            pass

        val = 1337
        with nullcontext(val) as res:
            self.assertEqual(res, val)


if __name__ == "__main__":
    import unittest

    unittest.main()
