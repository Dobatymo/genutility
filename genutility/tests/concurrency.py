import threading
import time

from genutility.concurrency import NotThreadSafe, ThreadPool, gather_all_unsorted, gather_any
from genutility.test import MyTestCase
from genutility.time import MeasureTime, iter_timer

TIME_DELTA = 0.2  # seconds


class ConcurrencyTest(MyTestCase):
    @staticmethod
    def sleep(sec):
        time.sleep(sec)
        return sec

    def setUp(self):
        self.threadpool = ThreadPool(3)

    def tearDown(self):
        del self.threadpool

    # gather_all_unsorted

    def test_gather_all_unsorted(self):
        inputs = (1, 2, 3)
        truths = ((0, 1), (1, 2), (2, 3))
        deltas = (1.0, 1.0, 1.0)

        for (result, truth, delta), messured_delta in iter_timer(
            zip(gather_all_unsorted(self.threadpool, self.sleep, inputs), truths, deltas)
        ):
            self.assertEqual(result, truth)
            self.assertAlmostEqual(messured_delta, delta, delta=TIME_DELTA)

    def test_gather_all_unsorted_inverse(self):
        inputs = (3, 2, 1)
        truths = ((2, 1), (1, 2), (0, 3))
        deltas = (1.0, 1.0, 1.0)

        for (result, truth, delta), messured_delta in iter_timer(
            zip(gather_all_unsorted(self.threadpool, self.sleep, inputs), truths, deltas)
        ):
            self.assertEqual(result, truth)
            self.assertAlmostEqual(messured_delta, delta, delta=TIME_DELTA)

    # gather_any

    def test_gather_any_first(self):
        truth = (0, 0)
        with MeasureTime() as t:
            result = gather_any(self.threadpool, self.sleep, (0, 1, 2))
        self.assertAlmostEqual(t.get(), 0.0, delta=TIME_DELTA)
        self.assertEqual(result, truth)

    def test_gather_any_last(self):
        truth = (2, 0)
        with MeasureTime() as t:
            result = gather_any(self.threadpool, self.sleep, (2, 1, 0))
        self.assertAlmostEqual(t.get(), 0.0, delta=TIME_DELTA)
        self.assertEqual(result, truth)

    def test_NotThreadSafe(self):
        @NotThreadSafe(True)
        class attr:
            test = 0

        class access(threading.Thread):
            def __init__(innerself, obj):
                threading.Thread.__init__(innerself)
                innerself.obj = obj

            def run(innerself):
                with self.assertRaises(RuntimeError):
                    innerself.obj.test = 2
                    self.assertEqual(innerself.obj.test, 2)

        obj = attr()
        obj.test = 1
        self.assertEqual(obj.test, 1)
        t = access(obj)
        t.start()
        t.join()


if __name__ == "__main__":
    import logging
    import unittest

    logging.warning("These unittests are time critical, they might fail if the system is under heavy load")
    unittest.main()
