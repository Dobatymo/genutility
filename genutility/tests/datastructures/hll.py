from __future__ import generator_stop

from genutility.datastructures.hll import HyperLogLog
from genutility.test import MyTestCase, parametrize


class HllTest(MyTestCase):

    @parametrize(
        (set(), 0),
        (set(["asd", "qwe"]), 0),
        (set(map(str, range(1000000))), 10000),
    )
    def test_HyperLogLog(self, values, delta):

        hll = HyperLogLog()
        hll.update(values)
        self.assertLessEqual(abs(len(values) - len(hll)), delta)

if __name__ == "__main__":
    import unittest
    unittest.main()
