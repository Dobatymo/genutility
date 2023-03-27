from genutility.datetime import now
from genutility.msgpack import dumps, loads, read_msgpack, write_msgpack
from genutility.test import MyTestCase, parametrize


class MsgpackTest(MyTestCase):
    @parametrize(
        (
            {
                "int": 43,
                "float": 13.37,
                "unicode": "你好",
                "bytes": b"asd",
                "datetime": now(),
                "set": {1, 2, 3},
                "frozenset": frozenset({1, 2, 3}),
                "tuple": (1, 2, 3),
            },
        ),
        ({1: 2, 3: 4},),
    )
    def test_dumps_loads(self, truth):
        result = loads(dumps(truth))
        self.assertEqual(truth, result)

    @parametrize(
        (
            {
                "int": 43,
                "float": 13.37,
                "unicode": "你好",
                "bytes": b"asd",
                "datetime": now(),
                "set": {1, 2, 3},
                "frozenset": frozenset({1, 2, 3}),
                "tuple": (1, 2, 3),
            },
        ),
        ({1: 2, 3: 4},),
    )
    def test_write_read(self, truth):
        path = "testtemp/read_write.msgpack"
        write_msgpack(truth, path)
        result = read_msgpack(path)
        self.assertEqual(truth, result)


if __name__ == "__main__":
    import unittest

    unittest.main()
