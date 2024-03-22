import datetime
import json
import logging
from io import StringIO

from genutility._file import CloseableNamedTemporaryFile
from genutility.json import (
    BuiltinRoundtripDecoder,
    BuiltinRoundtripEncoder,
    JsonLinesFormatter,
    json_lines,
    read_json_lines,
)
from genutility.test import MyTestCase, parametrize


class JsonTest(MyTestCase):
    @parametrize(("", tuple()), ('{"asd": 1}\n["asd", 1]\n', ({"asd": 1}, ["asd", 1])))
    def test_json_lines_from_stream(self, content, truth):
        stream = StringIO(content)
        with json_lines.from_stream(stream) as fr:
            result = tuple(fr)

        self.assertEqual(truth, result)

    @parametrize(("", tuple()), ('{"asd": 1}\n["asd", 1]\n', ({"asd": 1}, ["asd", 1])))
    def test_read_json_lines(self, content, truth):
        with CloseableNamedTemporaryFile(mode="wt", encoding="utf-8") as (f, fname):
            f.write(content)
            f.close()  # Windows compatibility, otherwise sharing violation
            result = tuple(read_json_lines(fname))

        self.assertEqual(truth, result)

    def test_JsonLinesFormatter(self):
        stream = StringIO()

        logger = logging.getLogger("JsonLinesFormatter")
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(stream)
        handler.setLevel(logging.INFO)
        jl_formatter = JsonLinesFormatter(include={"datetime-str"}, builtins={"thread"})
        handler.setFormatter(jl_formatter)
        logger.addHandler(handler)

        logger.info({"key": "test"})
        d = json.loads(stream.getvalue())

        self.assertEqual(d["key"], "test")
        self.assertIn("datetime-str", d)
        self.assertIn("thread", d)

    def test_BuiltinRoundtripDecoder(self):
        dt = datetime.datetime(2000, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
        raw = '{"dt": {"$datetime": "2000-01-01T00:00:00+00:00"}, "set": {"$set": [1, 2, 3]}}'

        truth = {"dt": dt, "set": {1, 2, 3}}
        result = json.loads(raw, cls=BuiltinRoundtripDecoder)
        self.assertEqual(truth, result)

    def test_BuiltinRoundtripEncoder(self):
        dt = datetime.datetime(2000, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
        truth = '{"dt": {"$datetime": "2000-01-01T00:00:00+00:00"}, "set": {"$set": [1, 2, 3]}}'
        result = json.dumps({"dt": dt, "set": {1, 2, 3}}, cls=BuiltinRoundtripEncoder)
        self.assertEqual(truth, result)


if __name__ == "__main__":
    import unittest

    unittest.main()
