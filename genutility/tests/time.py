from genutility.test import MyTestCase
from genutility.time import DeltaTime, TimeIt


class TimeTest(MyTestCase):
    def test_delta_time(self):
        delta = DeltaTime()

        self.assertIs(delta, iter(delta))
        self.assertGreaterEqual(next(delta), 0)
        self.assertGreaterEqual(delta.get_reset(), 0)

    def test_timeit(self):
        timer = TimeIt()

        self.assertEqual(3, timer("add", lambda a, b: a + b, 1, 2))
        self.assertEqual(1, timer.length("add"))
        self.assertGreaterEqual(timer.min("add"), 0)


if __name__ == "__main__":
    import unittest

    unittest.main()
