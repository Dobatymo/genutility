import pickle  # nosec: B403
import unittest
from sqlite3 import sqlite_version_info
from time import sleep

from genutility.exceptions import NoResult
from genutility.filesdb import FileDbHistory, FileDbSimple
from genutility.test import MyTestCase


class Simple(FileDbSimple):
    @classmethod
    def derived(cls):
        return [
            ("data", "VARCHAR(10)", "?"),
        ]


class History(FileDbHistory):
    @classmethod
    def derived(cls):
        return [
            ("data", "VARCHAR(10)", "?"),
        ]


class History2(FileDbHistory):
    @classmethod
    def derived(cls):
        return [
            ("data1", "VARCHAR(10)", "?"),
            ("data2", "VARCHAR(10)", "?"),
        ]


class SimpleDBTest(MyTestCase):
    def test_pickle(self):
        db = Simple(":memory:", "tests")
        data = pickle.dumps(db)
        db2 = pickle.loads(data)  # nosec: B301
        assert db._get_latest_sql.cache_info().currsize == 0
        assert db2._get_latest_sql.cache_info().currsize == 0

    def test_a(self):
        db = Simple(":memory:", "tests")

        result = db.add_file("path/pathB", 123, "2013-01-01 12:00:00", derived={"data": "asd"})
        assert result

        assert list(db.iter(no=("entry_date",))) == [("path/pathB", 123, "2013-01-01 12:00:00", "asd")]

        row = db.get_latest("path/pathB", 123, "2013-01-01 12:00:00", no=("entry_date",))
        assert row == ("path/pathB", 123, "2013-01-01 12:00:00", "asd")

        result = db.add_file("path/pathB", 123, "2013-01-01 12:00:00", derived={"data": "asd"})
        assert not result

        result = db.add_file("path/pathB", 123, "2013-01-01 12:00:00", derived={"data": "qwe"})
        assert result

        result = db.add_file("path/pathB", 124, "2013-01-01 12:00:00", derived={"data": "qwe"})
        assert result

        assert list(db.iter(no=("entry_date",))) == [("path/pathB", 124, "2013-01-01 12:00:00", "qwe")]

        with self.assertRaises(NoResult):
            row = db.get_latest("path/pathB", 123, "2013-01-01 12:00:00", no=("entry_date",))

        row = db.get_latest("path/pathB", 124, "2013-01-01 12:00:00", no=("entry_date",))
        assert row == ("path/pathB", 124, "2013-01-01 12:00:00", "qwe")

    def test_add_file(self):
        db = Simple(":memory:", "tests")

        result = db.add_file("path/pathB", 123, "2013-01-01 12:00:00", derived={"data": "asd1"})
        assert result
        assert len(db) == 1
        assert list(db.iter(no=("entry_date",))) == [("path/pathB", 123, "2013-01-01 12:00:00", "asd1")]
        result = db.get_latest("path/pathB", 123, "2013-01-01 12:00:00", no=("entry_date",))
        assert result == ("path/pathB", 123, "2013-01-01 12:00:00", "asd1")
        result = db.get_latest(
            "path/pathB", 123, "2013-01-01 12:00:00", derived={"data": "asd1"}, no=("entry_date",), ignore_null=False
        )
        assert result == ("path/pathB", 123, "2013-01-01 12:00:00", "asd1")
        with self.assertRaises(NoResult):
            db.get_latest("path/pathB", 123, "2013-01-01 12:00:00", ignore_null=False)

        result = db.add_file("path/pathB", 123, "2013-01-01 12:00:00", derived={"data": "asd1"})
        assert not result
        assert len(db) == 1
        assert list(db.iter(no=("entry_date",))) == [("path/pathB", 123, "2013-01-01 12:00:00", "asd1")]

        result = db.add_file("path/pathB", 123, "2013-01-01 12:00:00", derived={"data": "asd2"})
        assert result
        assert len(db) == 1
        assert list(db.iter(no=("entry_date",))) == [("path/pathB", 123, "2013-01-01 12:00:00", "asd2")]

        result = db.add_file("path/pathB", 123, "2013-01-01 12:00:00")
        assert not result
        assert len(db) == 1
        assert list(db.iter(no=("entry_date",))) == [("path/pathB", 123, "2013-01-01 12:00:00", "asd2")]

    def test_add_file_replace(self):
        db = Simple(":memory:", "tests")

        db._add_file(("path", 100, "2013-01-01 12:00:00"), derived={"data": "asd"})
        assert list(db.iter(no=("entry_date",))) == [("path", 100, "2013-01-01 12:00:00", "asd")]

        db._add_file(("path", 100, "2013-01-01 12:00:00"), derived={"data": "asd"})
        assert list(db.iter(no=("entry_date",))) == [("path", 100, "2013-01-01 12:00:00", "asd")]

        db._add_file(("path", 100, "2013-01-01 12:00:00"), derived={"data": "qwe"})
        assert list(db.iter(no=("entry_date",))) == [("path", 100, "2013-01-01 12:00:00", "qwe")]

        db._add_file(("path", 200, "2013-01-01 12:00:00"), derived={"data": "asd"})
        assert list(db.iter(no=("entry_date",))) == [("path", 200, "2013-01-01 12:00:00", "asd")]

        db._add_file(("path2", 100, "2013-01-01 12:00:00"), derived={"data": "asd"})
        assert list(db.iter(no=("entry_date",))) == [
            ("path", 200, "2013-01-01 12:00:00", "asd"),
            ("path2", 100, "2013-01-01 12:00:00", "asd"),
        ]

        db._add_file(("path2", 100, "2013-01-01 12:00:00"), derived={})
        assert list(db.iter(no=("entry_date",))) == [
            ("path", 200, "2013-01-01 12:00:00", "asd"),
            ("path2", 100, "2013-01-01 12:00:00", None),
        ]

    def test_add_file_replace_batch(self):
        db = Simple(":memory:", "tests")

        mandatory = [
            ("path1", 100, "2013-01-01 12:00:00"),
            ("path2", 100, "2013-01-01 12:00:00"),
        ]
        derived = [
            {"data": "asd"},
            {"data": "qwe"},
        ]
        db._add_file_many(mandatory, ["data"], derived)
        assert list(db.iter(no=("entry_date",))) == [
            ("path1", 100, "2013-01-01 12:00:00", "asd"),
            ("path2", 100, "2013-01-01 12:00:00", "qwe"),
        ]

        mandatory = [
            ("path", 100, "2013-01-01 12:00:00"),
            ("path", 100, "2013-01-01 12:00:00"),
        ]
        derived = [
            {"data": "asd"},
            {"data": "qwe"},
        ]
        db._add_file_many(mandatory, ["data"], derived)
        assert list(db.iter(no=("entry_date",))) == [
            ("path1", 100, "2013-01-01 12:00:00", "asd"),
            ("path2", 100, "2013-01-01 12:00:00", "qwe"),
            ("path", 100, "2013-01-01 12:00:00", "qwe"),
        ]

        mandatory = [
            ("path", 100, "2013-01-01 12:00:00"),
            ("path", 200, "2013-01-01 12:00:00"),
        ]
        derived = [
            {"data": "qwe"},
            {"data": "qwe"},
        ]
        db._add_file_many(mandatory, ["data"], derived)
        assert list(db.iter(no=("entry_date",))) == [
            ("path1", 100, "2013-01-01 12:00:00", "asd"),
            ("path2", 100, "2013-01-01 12:00:00", "qwe"),
            ("path", 200, "2013-01-01 12:00:00", "qwe"),
        ]

        mandatory = [
            ("path", 200, "2013-01-01 12:00:00"),
            ("path", 200, "2013-01-01 12:00:00"),
        ]
        derived = [
            {"data": "qwe"},
            {"data": None},
        ]
        db._add_file_many(mandatory, ["data"], derived)
        assert list(db.iter(no=("entry_date",))) == [
            ("path1", 100, "2013-01-01 12:00:00", "asd"),
            ("path2", 100, "2013-01-01 12:00:00", "qwe"),
            ("path", 200, "2013-01-01 12:00:00", None),
        ]

    @unittest.skipIf(sqlite_version_info < (3, 35, 0), "SQLite 3.35.0 or higher required")
    def test_add_file_upsert(self):
        db = Simple(":memory:", "tests")

        db._add_file(("path", 100, "2013-01-01 12:00:00"), derived={"data": "asd"}, replace=False)
        assert list(db.iter(no=("entry_date",))) == [("path", 100, "2013-01-01 12:00:00", "asd")]

        db._add_file(("path", 100, "2013-01-01 12:00:00"), derived={"data": "asd"}, replace=False)
        assert list(db.iter(no=("entry_date",))) == [("path", 100, "2013-01-01 12:00:00", "asd")]

        db._add_file(("path", 100, "2013-01-01 12:00:00"), derived={"data": "qwe"}, replace=False)
        assert list(db.iter(no=("entry_date",))) == [("path", 100, "2013-01-01 12:00:00", "qwe")]

        db._add_file(("path", 200, "2013-01-01 12:00:00"), derived={"data": "asd"}, replace=False)
        assert list(db.iter(no=("entry_date",))) == [("path", 200, "2013-01-01 12:00:00", "asd")]

        db._add_file(("path2", 100, "2013-01-01 12:00:00"), derived={"data": "asd"}, replace=False)
        assert list(db.iter(no=("entry_date",))) == [
            ("path", 200, "2013-01-01 12:00:00", "asd"),
            ("path2", 100, "2013-01-01 12:00:00", "asd"),
        ]

        db._add_file(("path2", 100, "2013-01-01 12:00:00"), derived={}, replace=False)
        assert list(db.iter(no=("entry_date",))) == [
            ("path", 200, "2013-01-01 12:00:00", "asd"),
            ("path2", 100, "2013-01-01 12:00:00", "asd"),
        ]

    @unittest.skipIf(sqlite_version_info < (3, 35, 0), "SQLite 3.35.0 or higher required")
    def test_add_file_upsert_2(self):
        db = Simple(":memory:", "tests")

        db._add_file(("path", 100, "2013-01-01 12:00:00"), derived={"data": "asd"}, replace=False)
        assert list(db.iter(no=("entry_date",))) == [("path", 100, "2013-01-01 12:00:00", "asd")]

        db._add_file(("path", 200, "2013-01-01 12:00:00"), derived={}, replace=False)
        assert list(db.iter(no=("entry_date",))) == [("path", 200, "2013-01-01 12:00:00", None)]

    @unittest.skipIf(sqlite_version_info < (3, 35, 0), "SQLite 3.35.0 or higher required")
    def test_add_file_upsert_2_batch(self):
        db = Simple(":memory:", "tests")

        mandatory = [
            ("path1", 100, "2013-01-01 12:00:00"),
            ("path2", 100, "2013-01-01 12:00:00"),
        ]
        derived = [
            {"data": "asd"},
            {"data": "asd"},
        ]
        truth = [("path1", 100, "2013-01-01 12:00:00", "asd"), ("path2", 100, "2013-01-01 12:00:00", "asd")]
        db._add_file_many(mandatory, ["data"], derived, replace=False)
        result = list(db.iter(no=("entry_date",)))
        self.assertEqual(truth, result)

        mandatory = [
            ("path1", 100, "2013-01-01 12:00:00"),
            ("path2", 200, "2013-01-01 12:00:00"),
        ]
        derived = [
            {},
            {},
        ]
        truth = [("path1", 100, "2013-01-01 12:00:00", "asd"), ("path2", 200, "2013-01-01 12:00:00", None)]
        db._add_file_many(mandatory, [], derived, replace=False)
        result = list(db.iter(no=("entry_date",)))
        self.assertEqual(truth, result)

    def test_get_latest_many(self):
        db = Simple(":memory:", "tests")

        db._add_file(("path1", 100, "2013-01-01 12:00:00"), derived={"data": "asd"})
        db._add_file(("path2", 100, "2013-01-01 12:00:00"), derived={"data": "qwe"})
        db._add_file(("path3", 100, "2013-01-01 12:00:00"), derived={"data": "zxc"})

        result = list(
            db.get_latest_many(
                [("path1", 100, "2013-01-01 12:00:00"), ("path2", 100, "2013-01-01 12:00:00")], 2, no=("entry_date",)
            )
        )
        assert result == [("path1", 100, "2013-01-01 12:00:00", "asd"), ("path2", 100, "2013-01-01 12:00:00", "qwe")]

        result = list(
            db.get_latest_many(
                [("path2", 100, "2013-01-01 12:00:00"), ("path1", 100, "2013-01-01 12:00:00")], 2, no=("entry_date",)
            )
        )
        assert result == [("path2", 100, "2013-01-01 12:00:00", "qwe"), ("path1", 100, "2013-01-01 12:00:00", "asd")]


class HistoryDBTest(MyTestCase):
    def test_a(self):
        db = History(":memory:", "tests")

        no = ("file_id", "entry_date")

        result = db.add_file("path/pathB", 123, "2013-01-01 12:00:00", derived={"data": "asd"})
        assert result

        assert list(db.iter(no=no)) == [("path/pathB", 123, "2013-01-01 12:00:00", "asd")]

        row = db.get_latest("path/pathB", 123, "2013-01-01 12:00:00", no=no)
        assert row == ("path/pathB", 123, "2013-01-01 12:00:00", "asd")

        result = db.add_file("path/pathB", 123, "2013-01-01 12:00:00", derived={"data": "asd"})
        assert not result

        sleep(2)  # sleep so sqlite date is increased

        result = db.add_file("path/pathB", 123, "2013-01-01 12:00:00", derived={"data": "qwe"})
        assert result

        result = db.add_file("path/pathB", 124, "2013-01-01 12:00:00", derived={"data": "qwe"})
        assert result

        assert list(db.iter(no=no)) == [
            ("path/pathB", 123, "2013-01-01 12:00:00", "asd"),
            ("path/pathB", 123, "2013-01-01 12:00:00", "qwe"),
            ("path/pathB", 124, "2013-01-01 12:00:00", "qwe"),
        ]

        row = db.get_latest("path/pathB", 123, "2013-01-01 12:00:00", no=no)
        assert row == ("path/pathB", 123, "2013-01-01 12:00:00", "qwe")

        row = db.get_latest("path/pathB", 124, "2013-01-01 12:00:00", no=no)
        assert row == ("path/pathB", 124, "2013-01-01 12:00:00", "qwe")

    def test_b(self):
        db = History2(":memory:", "tests")

        no = ("file_id", "entry_date")

        result = db.add_file("path/pathB", 123, "2013-01-01 12:00:00", derived={"data1": "asd"})
        assert result

        assert list(db.iter(no=no)) == [("path/pathB", 123, "2013-01-01 12:00:00", "asd", None)]

        row = db.get_latest("path/pathB", 123, "2013-01-01 12:00:00", no=no)
        assert row == ("path/pathB", 123, "2013-01-01 12:00:00", "asd", None)

        result = db.add_file("path/pathB", 123, "2013-01-01 12:00:00", derived={"data1": "asd"})
        assert not result

        sleep(2)  # sleep so sqlite date is increased

        result = db.add_file("path/pathB", 123, "2013-01-01 12:00:00", derived={"data1": "qwe"})
        assert result

        result = db.add_file("path/pathB", 124, "2013-01-01 12:00:00", derived={"data1": "qwe"})
        assert result

        assert list(db.iter(no=no)) == [
            ("path/pathB", 123, "2013-01-01 12:00:00", "asd", None),
            ("path/pathB", 123, "2013-01-01 12:00:00", "qwe", None),
            ("path/pathB", 124, "2013-01-01 12:00:00", "qwe", None),
        ]

        row = db.get_latest("path/pathB", 123, "2013-01-01 12:00:00", no=no)
        assert row == ("path/pathB", 123, "2013-01-01 12:00:00", "qwe", None)

        row = db.get_latest("path/pathB", 124, "2013-01-01 12:00:00", no=no)
        assert row == ("path/pathB", 124, "2013-01-01 12:00:00", "qwe", None)

    def test_get_latest_many(self):
        db = History(":memory:", "tests")

        db._add_file(("path1", 100, "2013-01-01 12:00:00"), derived={"data": "asd"})
        db._add_file(("path2", 100, "2013-01-01 12:00:00"), derived={"data": "qwe"})
        db._add_file(("path3", 100, "2013-01-01 12:00:00"), derived={"data": "zxc"})

        result = list(
            db.get_latest_many(
                [("path1", 100, "2013-01-01 12:00:00"), ("path2", 100, "2013-01-01 12:00:00")], 2, no=("entry_date",)
            )
        )
        assert result == [
            (1, "path1", 100, "2013-01-01 12:00:00", "asd"),
            (2, "path2", 100, "2013-01-01 12:00:00", "qwe"),
        ]

        result = list(
            db.get_latest_many(
                [("path2", 100, "2013-01-01 12:00:00"), ("path1", 100, "2013-01-01 12:00:00")], 2, no=("entry_date",)
            )
        )
        assert result == [
            (2, "path2", 100, "2013-01-01 12:00:00", "qwe"),
            (1, "path1", 100, "2013-01-01 12:00:00", "asd"),
        ]

        sleep(2)
        db._add_file(("path3", 100, "2013-01-01 12:00:00"), derived={"data": "new"})

        result = list(
            db.get_latest_many(
                [("path1", 100, "2013-01-01 12:00:00"), ("path3", 100, "2013-01-01 12:00:00")], 2, no=("entry_date",)
            )
        )
        assert result == [
            (1, "path1", 100, "2013-01-01 12:00:00", "asd"),
            (4, "path3", 100, "2013-01-01 12:00:00", "new"),
        ]


if __name__ == "__main__":
    unittest.main()
