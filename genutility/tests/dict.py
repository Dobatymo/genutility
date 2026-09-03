from genutility.dict import (
    KeyExistsError,
    NoOverwriteDict,
    flatten_keys,
    get_schema_simple,
    keydefaultdict,
    mapmap,
    rec_update,
    rec_update_mod,
    subdict,
    subdictdefault,
    zipget,
)
from genutility.test import MyTestCase, parametrize


class DictTest(MyTestCase):
    @parametrize(
        ({1: "a", 2: "b", 3: "c"}, (1, 2, 3), ("a", "b", "c")),
    )
    def test_mapmap(self, d, it, truth):
        result = mapmap(d, it)
        self.assertIterEqual(result, truth)

    @parametrize(
        ({}, (), {}),
        ({1: 2, 3: 4, 5: 6}, (), {}),
        ({1: 2, 3: 4, 5: 6}, (1, 3, 5), {1: 2, 3: 4, 5: 6}),
    )
    def test_subdict(self, d, it, truth):
        result = subdict(d, it)
        self.assertEqual(truth, result)

    @parametrize(
        ({}, (1, 3, 5), {}),
    )
    def test_subdict_error(self, d, it, truth):
        with self.assertRaises(KeyError):
            subdict(d, it)

    @parametrize(
        ({}, (), None, {}),
        ({1: 2, 3: 4, 5: 6}, (), None, {}),
        ({1: 2, 3: 4, 5: 6}, (1, 3, 5), None, {1: 2, 3: 4, 5: 6}),
        ({}, (1, 3, 5), None, {1: None, 3: None, 5: None}),
    )
    def test_subdictdefault(self, d, it, default, truth):
        result = subdictdefault(d, it, default)
        self.assertEqual(truth, result)

    @parametrize(
        (lambda x: x, "test", "test"),
        (lambda x: x * 2, 1, 2),
    )
    def test_keydefaultdict(self, func, key, truth):
        d = keydefaultdict(func)
        self.assertEqual(truth, d[key])

    def test_keydefaultdict_error(self):
        d = keydefaultdict()
        with self.assertRaises(KeyError):
            d["test"]

    def test_NoOverwriteDict(self):
        d = NoOverwriteDict()

        d[1] = 1
        with self.assertRaises(KeyExistsError):
            d[1] = 2

        d.update({2: 2})
        with self.assertRaises(KeyExistsError):
            d.update({2: 3})

        self.assertEqual(d, {1: 1, 2: 2})

    def test_get_schema_simple(self):
        d = [{"a": 1}, {"a": 2, "b": "asd"}, {"c": [1, 2]}, {"c": [3], "d": [{"a": 1.1}]}]
        result = get_schema_simple(d)
        truth = {
            "a": "int16",
            "b": "str",
            "c": ["int16"],
            "d": [{"a": "float"}],
        }
        self.assertEqual(truth, result)

    def test_get_schema_simple_list_options(self):
        self.assertEqual(
            {"value": ["float"]},
            get_schema_simple([{"value": [1]}, {"value": [1.5]}], int_to_float=True),
        )
        self.assertEqual(
            {"value": ["int16"]},
            get_schema_simple([{"value": [None]}, {"value": [1]}], ignore_none=True),
        )

    def test_get_schema_simple_truncates_nested_list_samples(self):
        result = get_schema_simple([{"value": [{"nested": [1, 2, 3]}]}])
        self.assertEqual({"value": [{"nested": ["int16"]}]}, result)

    def test_get_schema_simple_nested_options(self):
        result = get_schema_simple(
            [
                {"value": None, "obj": {"value": None}, "rows": [{"value": None}]},
                {"value": 1, "obj": {"value": 1}, "rows": [{"value": 1}]},
                {"value": None, "obj": {"value": None}, "rows": [{"value": None}]},
            ],
            ignore_none=True,
        )
        self.assertEqual(
            {"value": "int16", "obj": {"value": "int16"}, "rows": [{"value": "int16"}]},
            result,
        )

        result = get_schema_simple(
            [{"obj": {"value": 1}, "rows": [{"value": 1}]}, {"obj": {"value": 1.5}, "rows": [{"value": 1.5}]}],
            int_to_float=True,
        )
        self.assertEqual(
            {"obj": {"value": "float"}, "rows": [{"value": "float"}]},
            result,
        )

    def test_get_schema_simple_empty_list_then_values(self):
        result = get_schema_simple([{"values": []}, {"values": [1, 2, 3]}])
        self.assertEqual({"values": ["int16"]}, result)

    @parametrize(
        (2**31 - 1, "int32"),
        (2**31, "uint32"),
        (2**32, "int64"),
        (2**63, "uint64"),
    )
    def test_get_schema_simple_integer_width(self, value, truth):
        self.assertEqual({"value": truth}, get_schema_simple([{"value": value}]))

    def test_get_schema_simple_uint32_boundary(self):
        self.assertEqual(
            {"value": "uint32"},
            get_schema_simple([{"value": 2498341375}]),
        )

    def test_get_schema_simple_bool(self):
        result = get_schema_simple(
            [
                {"flag": True, "flags": [True, False], "nested": {"flag": False}},
                {"flag": False, "flags": [False], "nested": {"flag": True}},
            ]
        )
        self.assertEqual(
            {"flag": "bool", "flags": ["bool"], "nested": {"flag": "bool"}},
            result,
        )

    def test_get_schema_simple_bool_is_not_int_to_float(self):
        with self.assertRaises(TypeError):
            get_schema_simple([{"value": True}, {"value": 1.5}], int_to_float=True)

        with self.assertRaises(TypeError):
            get_schema_simple([{"value": [True]}, {"value": [1.5]}], int_to_float=True)

    @parametrize(
        ([[1, 2], [3, 4]], [0, 1], [1, 4]),
    )
    def test_zipget(self, objs, keys, truth):
        result = zipget(objs, keys)
        self.assertIterEqual(truth, result)

    @parametrize(
        ({}, {}),
        ({1: 2}, {(1,): 2}),
        ({1: {2: 3}}, {(1, 2): 3}),
        ({1: {2: 3}, 4: 5}, {(1, 2): 3, (4,): 5}),
        ({1: {2: 3, 4: 5}}, {(1, 2): 3, (1, 4): 5}),
    )
    def test_flatten_keys(self, d, truth):
        result = flatten_keys(d)
        self.assertEqual(truth, result)

    @parametrize(
        ({}, {}, {}),
        ({}, {1: 2}, {1: 2}),
        ({1: 2}, {}, {1: 2}),
        ({1: 2}, {3: 4}, {1: 2, 3: 4}),
        ({1: {2: 3}}, {1: {4: 5}}, {1: {2: 3, 4: 5}}),
        ({1: {2: 3, 4: 5}}, {1: {4: 6}}, {1: {2: 3, 4: 6}}),
    )
    def test_rec_update(self, d, u, truth):
        rec_update(d, u)
        self.assertEqual(truth, d)

    @parametrize(
        ({}, {}, {}),
        ({}, {1: 2}, {1: 2}),
        ({1: 2}, {}, {1: 2}),
        ({1: 2}, {3: 4}, {1: 2, 3: 4}),
        ({1: {2: 3}}, {1: {4: 5}}, {1: {2: 3, 4: 5}}),
        ({1: {2: 3, 4: 5}}, {1: {4: 6}}, {1: {2: 3, 4: 6}}),
    )
    def test_rec_update_mod(self, d, u, truth):
        rec_update_mod(d, u)
        self.assertEqual(truth, d)


if __name__ == "__main__":
    import unittest

    unittest.main()
