import random
from operator import add
from sys import maxsize

from genutility.math import minmax
from genutility.segment_tree import SegmentTree
from genutility.test import MyTestCase


def range_generator(size, tests):
    ls = random.sample(range(size), tests)
    rs = random.sample(range(size), tests)

    for left, right in zip(ls, rs):
        if left == right:
            continue

        yield minmax(left, right)


class SegmentTreeTest(MyTestCase):
    def test_range(self):
        size = 100
        tests = 10

        t = list(range(size))
        random.shuffle(t)

        for func, initializer, truthfunc in ((min, maxsize, min), (max, -maxsize, max), (add, 0, sum)):
            st = SegmentTree(t, func, initializer)
            st.build()

            for left, right in range_generator(size, tests):

                result = st.query(left, right)
                truth = truthfunc(t[left:right])
                self.assertEqual(truth, result)


if __name__ == "__main__":
    import unittest

    unittest.main()
