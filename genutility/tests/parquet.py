import pyarrow as pa

from genutility.parquet import schema_simple_to_pq
from genutility.test import MyTestCase


class ParquetTest(MyTestCase):
    def test_schema_simple_to_pq_supports_float(self):
        schema = schema_simple_to_pq({"value": "float"})
        self.assertEqual(pa.float64(), schema.field("value").type)
        self.assertEqual(pa.float32(), schema_simple_to_pq({"value": "float"}, float_bits=32).field("value").type)


if __name__ == "__main__":
    import unittest

    unittest.main()
