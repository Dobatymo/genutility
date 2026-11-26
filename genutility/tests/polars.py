from io import StringIO
from itertools import islice
from unittest import skipIf

import numpy as np
from importlib_metadata import PackageNotFoundError
from importlib_metadata import version as get_version
from packaging.version import Version

try:
    OLD_POLARS = Version(get_version("polars")) < Version("1.18")
except PackageNotFoundError:
    OLD_POLARS = True
else:
    import polars as pl

    from genutility.polars import pl_index, pl_islice, schema_simple_to_polars

from genutility.test import MyTestCase, parametrize


@skipIf(OLD_POLARS, "polars<1.18 or not installed")
class PolarsTest(MyTestCase):
    def test_pl_index(self):
        s = list("abcdefghij")
        df = pl.DataFrame({"a": s})
        ind = np.array([1, 3, 8])
        result = pl_index(df, ind)
        truth = pl.DataFrame({"a": ["b", "d", "i"]})
        self.assertTrue(truth.equals(result))

    @parametrize(
        (None,),
        (1,),
        (1, None),
        (1, 2),
        (None, 2),
    )
    def test_pl_islice(self, *args):
        s = list("abcdefghij")
        df = pl.DataFrame({"a": s})

        truth = list(islice(s, *args))
        result = pl_islice(df, *args)["a"].to_list()
        self.assertEqual(truth, result)

    def test_schema_simple_to_polars(self):
        schema = schema_simple_to_polars({"id": "int32", "value": "float", "nested": [{"name": "str"}]})
        self.assertEqual(pl.Int32, schema["id"])
        self.assertEqual(pl.UInt32, schema_simple_to_polars({"value": "uint32"})["value"])
        self.assertEqual(pl.Float64, schema["value"])
        self.assertEqual(pl.List(pl.Struct({"name": pl.String})), schema["nested"])
        self.assertEqual(pl.Float32, schema_simple_to_polars({"value": "float"}, float_bits=32)["value"])

    def test_schema_simple_to_polars_nulls_and_empty_lists(self):
        simple = {
            "null": "NoneType",
            "empty": [],
            "null_items": ["NoneType"],
            "nested": {"optional": "NoneType", "items": []},
            "records": [{"optional": "NoneType", "items": []}],
        }
        schema = schema_simple_to_polars(simple)
        self.assertEqual(pl.Null, schema["null"])
        self.assertEqual(pl.List(pl.Null), schema["empty"])
        self.assertEqual(pl.List(pl.Null), schema["null_items"])
        nested = pl.Struct({"optional": pl.Null, "items": pl.List(pl.Null)})
        self.assertEqual(nested, schema["nested"])
        self.assertEqual(pl.List(nested), schema["records"])

    def test_schema_simple_to_polars_preserves_integer_widths_by_default(self):
        schema = schema_simple_to_polars({"signed": "int16", "unsigned": "uint16"})
        self.assertEqual(pl.Int16, schema["signed"])
        self.assertEqual(pl.UInt16, schema["unsigned"])

    @parametrize((32,), (64,))
    def test_schema_simple_to_polars_min_integer_width(self, bits):
        signed = pl.Int32 if bits == 32 else pl.Int64
        unsigned = pl.UInt32 if bits == 32 else pl.UInt64
        schema = schema_simple_to_polars(
            {
                "signed": "int16",
                "unsigned": "uint16",
                "large": "int64",
                "items": ["int16"],
                "nested": [{"confidence": "int16"}],
            },
            min_int_bits=bits,
        )
        self.assertEqual(signed, schema["signed"])
        self.assertEqual(unsigned, schema["unsigned"])
        self.assertEqual(pl.Int64, schema["large"])
        self.assertEqual(pl.List(signed), schema["items"])
        self.assertEqual(pl.List(pl.Struct({"confidence": signed})), schema["nested"])

    def test_schema_simple_to_polars_ndjson_compatibility(self):
        schema = schema_simple_to_polars(
            {"lineno": "int16", "outputs": [{"confidence": "int16"}], "unused": "NoneType", "empty": []},
            min_int_bits=32,
        )
        frame = pl.read_ndjson(
            StringIO('{"lineno":42,"outputs":[{"confidence":3}],"unused":null,"empty":[]}\n'), schema=schema
        )
        self.assertEqual(
            [{"lineno": 42, "outputs": [{"confidence": 3}], "unused": None, "empty": []}], frame.to_dicts()
        )

    def test_schema_simple_to_polars_option_validation(self):
        for bits in (0, 12, 128):
            with self.assertRaises(ValueError):
                schema_simple_to_polars({}, min_int_bits=bits)
        with self.assertRaises(ValueError):
            schema_simple_to_polars({}, float_bits=16)


if __name__ == "__main__":
    import unittest

    unittest.main()
