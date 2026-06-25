from genutility.bench import MeasureMemory
from genutility.test import MyTestCase


class BenchTest(MyTestCase):
    def test_measure_memory(self):
        with MeasureMemory() as mm:
            bytearray(1)

        self.assertIsInstance(mm.get(), int)


if __name__ == "__main__":
    import unittest

    unittest.main()
