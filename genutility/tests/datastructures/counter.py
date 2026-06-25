from genutility.datastructures.counter import MultiCounter
from genutility.test import MyTestCase


class MultiCounterTest(MyTestCase):
    def test_transform(self):
        counter = MultiCounter(str.lower)
        counter.add("a", "X")
        counter.update([("a", "Y")])

        self.assertEqual({"a": {"x": 0, "y": 0}}, dict(counter.items()))


if __name__ == "__main__":
    import unittest

    unittest.main()
