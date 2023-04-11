import unittest
from time import sleep

from genutility.exceptions import NoResult
from genutility.filesdb import FileDbHistory, FileDbSimple, GenericDb
from genutility.test import MyTestCase


class SimpleGenericNoPrimary(GenericDb):
    @classmethod
    def primary(cls):
        return [
            ("primary_1", "INTEGER NOT NULL PRIMARY KEY", "?"),
        ]

    @classmethod
    def auto(cls):
        return [
            ("auto_1", "INTEGER", "last_insert_rowid()"),
        ]

    @classmethod
    def mandatory(cls):
        return [
            ("mandatory_1", "INTEGER", "?"),
            ("mandatory_2", "INTEGER", "?"),
        ]

    @classmethod
    def derived(cls):
        return [
            ("derived_1", "INTEGER", "?"),
            ("derived_2", "INTEGER", "?"),
        ]


class SimpleGenericPrimary(GenericDb):
    @classmethod
    def primary(cls):
        return []

    @classmethod
    def auto(cls):
        return [
            ("auto_1", "INTEGER", "last_insert_rowid()"),
        ]

    @classmethod
    def mandatory(cls):
        return [
            ("mandatory_1", "INTEGER NOT NULL PRIMARY KEY", "?"),
            ("mandatory_2", "INTEGER", "?"),
        ]

    @classmethod
    def derived(cls):
        return [
            ("derived_1", "INTEGER", "?"),
            ("derived_2", "INTEGER", "?"),
        ]


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


class GenericDbTest(MyTestCase):
    def test_add_row_no_dup_no_primary(self):
        db = SimpleGenericNoPrimary(":memory:", "tests")

        # add data
        result = db._add_row_no_dup((1, 2), derived={"derived_1": 3})
        assert result
        assert list(db.iter()) == [(1, 0, 1, 2, 3, None)]

        # adding exactly the same data fails
        result = db._add_row_no_dup((1, 2), derived={"derived_1": 3})
        assert not result
        assert list(db.iter()) == [(1, 0, 1, 2, 3, None)]

        # adding additional data succeeds
        result = db._add_row_no_dup((1, 2), derived={"derived_1": 3, "derived_2": 4})
        assert result
        assert list(db.iter()) == [(1, 0, 1, 2, 3, None), (2, 1, 1, 2, 3, 4)]

        # adding data with changed derived data succeeds
        result = db._add_row_no_dup((1, 2), derived={"derived_1": 4})
        assert result
        assert list(db.iter()) == [(1, 0, 1, 2, 3, None), (2, 1, 1, 2, 3, 4), (3, 2, 1, 2, 4, None)]

        # adding data with changed mandatory data succeeds
        result = db._add_row_no_dup((1, 3), derived={"derived_1": 4})
        assert result
        assert list(db.iter()) == [
            (1, 0, 1, 2, 3, None),
            (2, 1, 1, 2, 3, 4),
            (3, 2, 1, 2, 4, None),
            (4, 3, 1, 3, 4, None),
        ]

    def test_add_row_no_dup_primary(self):
        db = SimpleGenericPrimary(":memory:", "tests")

        # add data
        result = db._add_row_no_dup((1, 2), derived={"derived_1": 3})
        assert result
        assert list(db.iter()) == [(0, 1, 2, 3, None)]

        # adding exactly the same data fails
        result = db._add_row_no_dup((1, 2), derived={"derived_1": 3})
        assert not result
        assert list(db.iter()) == [(0, 1, 2, 3, None)]

        # adding same data with additional data succeeds (overwrites the row)
        result = db._add_row_no_dup((1, 2), derived={"derived_1": 3, "derived_2": 4})
        assert result
        assert list(db.iter()) == [(1, 1, 2, 3, 4)]

        # adding same data with changed derived data succeeds (overwrites the row and resets derived)
        result = db._add_row_no_dup((1, 2), derived={"derived_1": 4})
        assert result
        assert list(db.iter()) == [(1, 1, 2, 4, None)]

        # adding data with changed mandatory (non-key) data succeeds (overwrites the row and resets derived)
        result = db._add_row_no_dup((1, 3), derived={"derived_2": 5})
        assert result
        assert list(db.iter()) == [(1, 1, 3, None, 5)]

        # adding data with changed mandatory (key) data succeeds (overwrites the row and resets derived)
        result = db._add_row_no_dup((2, 3), derived={"derived_1": 4})
        assert result
        assert list(db.iter()) == [(1, 1, 3, None, 5), (1, 2, 3, 4, None)]


class SimpleDBTest:  # MyTestCase
    def test_a(self):
        db = Simple(":memory:", "tests")

        result = db.add_file("path/pathB", 123, "2013-01-01 12:00:00", derived={"data": "asd"})
        assert result

        assert list(db.iter(no={"entry_date"})) == [("path/pathB", 123, "2013-01-01 12:00:00", "asd")]

        row = db.get_latest("path/pathB", 123, "2013-01-01 12:00:00", no={"entry_date"})
        assert row == ("path/pathB", 123, "2013-01-01 12:00:00", "asd")

        result = db.add_file("path/pathB", 123, "2013-01-01 12:00:00", derived={"data": "asd"})
        assert not result

        result = db.add_file("path/pathB", 123, "2013-01-01 12:00:00", derived={"data": "qwe"})
        assert result

        result = db.add_file("path/pathB", 124, "2013-01-01 12:00:00", derived={"data": "qwe"})
        assert result

        assert list(db.iter(no={"entry_date"})) == [("path/pathB", 124, "2013-01-01 12:00:00", "qwe")]

        with self.assertRaises(NoResult):
            row = db.get_latest("path/pathB", 123, "2013-01-01 12:00:00", no={"entry_date"})

        row = db.get_latest("path/pathB", 124, "2013-01-01 12:00:00", no={"entry_date"})
        assert row == ("path/pathB", 124, "2013-01-01 12:00:00", "qwe")

    def test_add_file(self):
        db = Simple(":memory:", "tests")

        result = db.add_file("path/pathB", 123, "2013-01-01 12:00:00", derived={"data": "asd1"})
        assert result
        assert len(db) == 1
        assert list(db.iter(no={"entry_date"})) == [("path/pathB", 123, "2013-01-01 12:00:00", "asd1")]
        result = db.get_latest("path/pathB", 123, "2013-01-01 12:00:00", no={"entry_date"})
        assert result == ("path/pathB", 123, "2013-01-01 12:00:00", "asd1")
        result = db.get_latest(
            "path/pathB", 123, "2013-01-01 12:00:00", derived={"data": "asd1"}, no={"entry_date"}, ignore_null=False
        )
        assert result == ("path/pathB", 123, "2013-01-01 12:00:00", "asd1")
        with self.assertRaises(NoResult):
            db.get_latest("path/pathB", 123, "2013-01-01 12:00:00", ignore_null=False)

        result = db.add_file("path/pathB", 123, "2013-01-01 12:00:00", derived={"data": "asd1"})
        assert not result
        assert len(db) == 1
        assert list(db.iter(no={"entry_date"})) == [("path/pathB", 123, "2013-01-01 12:00:00", "asd1")]

        result = db.add_file("path/pathB", 123, "2013-01-01 12:00:00", derived={"data": "asd2"})
        assert result
        assert len(db) == 1
        assert list(db.iter(no={"entry_date"})) == [("path/pathB", 123, "2013-01-01 12:00:00", "asd2")]

        result = db.add_file("path/pathB", 123, "2013-01-01 12:00:00")
        assert not result
        assert len(db) == 1
        assert list(db.iter(no={"entry_date"})) == [("path/pathB", 123, "2013-01-01 12:00:00", "asd2")]

    def test_add_row_replace(self):
        db = Simple(":memory:", "tests")

        db._add_row(("path", 100, "2013-01-01 12:00:00"), derived={"data": "asd"})
        assert list(db.iter(no={"entry_date"})) == [("path", 100, "2013-01-01 12:00:00", "asd")]

        db._add_row(("path", 100, "2013-01-01 12:00:00"), derived={"data": "asd"})
        assert list(db.iter(no={"entry_date"})) == [("path", 100, "2013-01-01 12:00:00", "asd")]

        db._add_row(("path", 100, "2013-01-01 12:00:00"), derived={"data": "qwe"})
        assert list(db.iter(no={"entry_date"})) == [("path", 100, "2013-01-01 12:00:00", "qwe")]

        db._add_row(("path", 200, "2013-01-01 12:00:00"), derived={"data": "asd"})
        assert list(db.iter(no={"entry_date"})) == [("path", 200, "2013-01-01 12:00:00", "asd")]

        db._add_row(("path2", 100, "2013-01-01 12:00:00"), derived={"data": "asd"})
        assert list(db.iter(no={"entry_date"})) == [
            ("path", 200, "2013-01-01 12:00:00", "asd"),
            ("path2", 100, "2013-01-01 12:00:00", "asd"),
        ]

        db._add_row(("path2", 100, "2013-01-01 12:00:00"), derived={})
        assert list(db.iter(no={"entry_date"})) == [
            ("path", 200, "2013-01-01 12:00:00", "asd"),
            ("path2", 100, "2013-01-01 12:00:00", None),
        ]

    def test_add_row_upsert(self):
        db = Simple(":memory:", "tests")

        db._add_row(("path", 100, "2013-01-01 12:00:00"), derived={"data": "asd"}, replace=False)
        assert list(db.iter(no={"entry_date"})) == [("path", 100, "2013-01-01 12:00:00", "asd")]

        db._add_row(("path", 100, "2013-01-01 12:00:00"), derived={"data": "asd"}, replace=False)
        assert list(db.iter(no={"entry_date"})) == [("path", 100, "2013-01-01 12:00:00", "asd")]

        db._add_row(("path", 100, "2013-01-01 12:00:00"), derived={"data": "qwe"}, replace=False)
        assert list(db.iter(no={"entry_date"})) == [("path", 100, "2013-01-01 12:00:00", "qwe")]

        db._add_row(("path", 200, "2013-01-01 12:00:00"), derived={"data": "asd"}, replace=False)
        assert list(db.iter(no={"entry_date"})) == [("path", 200, "2013-01-01 12:00:00", "asd")]

        db._add_row(("path2", 100, "2013-01-01 12:00:00"), derived={"data": "asd"}, replace=False)
        assert list(db.iter(no={"entry_date"})) == [
            ("path", 200, "2013-01-01 12:00:00", "asd"),
            ("path2", 100, "2013-01-01 12:00:00", "asd"),
        ]

        db._add_row(("path2", 100, "2013-01-01 12:00:00"), derived={}, replace=False)
        assert list(db.iter(no={"entry_date"})) == [
            ("path", 200, "2013-01-01 12:00:00", "asd"),
            ("path2", 100, "2013-01-01 12:00:00", "asd"),
        ]

    @unittest.skip("`GenericFileDb._add_row(..., replace=False)` still buggy")
    def test_add_row_upsert_2(self):
        db = Simple(":memory:", "tests")

        db._add_row(("path", 100, "2013-01-01 12:00:00"), derived={"data": "asd"}, replace=False)
        assert list(db.iter(no={"entry_date"})) == [("path", 100, "2013-01-01 12:00:00", "asd")]

        db._add_row(("path", 200, "2013-01-01 12:00:00"), derived={}, replace=False)
        assert list(db.iter(no={"entry_date"})) == [("path", 200, "2013-01-01 12:00:00", None)]

    def test_get_latest_many(self):
        db = Simple(":memory:", "tests")

        db._add_row(("path1", 100, "2013-01-01 12:00:00"), derived={"data": "asd"})
        db._add_row(("path2", 100, "2013-01-01 12:00:00"), derived={"data": "qwe"})
        db._add_row(("path3", 100, "2013-01-01 12:00:00"), derived={"data": "zxc"})

        result = list(
            db.get_latest_many(
                [("path1", 100, "2013-01-01 12:00:00"), ("path2", 100, "2013-01-01 12:00:00")], 2, no={"entry_date"}
            )
        )
        assert result == [("path1", 100, "2013-01-01 12:00:00", "asd"), ("path2", 100, "2013-01-01 12:00:00", "qwe")]

        result = list(
            db.get_latest_many(
                [("path2", 100, "2013-01-01 12:00:00"), ("path1", 100, "2013-01-01 12:00:00")], 2, no={"entry_date"}
            )
        )
        assert result == [("path2", 100, "2013-01-01 12:00:00", "qwe"), ("path1", 100, "2013-01-01 12:00:00", "asd")]


class HistoryDBTest:  # MyTestCase
    def test_a(self):
        db = History(":memory:", "tests")

        no = {"file_id", "entry_date"}

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

        no = {"file_id", "entry_date"}

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

        db._add_row(("path1", 100, "2013-01-01 12:00:00"), derived={"data": "asd"})
        db._add_row(("path2", 100, "2013-01-01 12:00:00"), derived={"data": "qwe"})
        db._add_row(("path3", 100, "2013-01-01 12:00:00"), derived={"data": "zxc"})

        result = list(
            db.get_latest_many(
                [("path1", 100, "2013-01-01 12:00:00"), ("path2", 100, "2013-01-01 12:00:00")], 2, no={"entry_date"}
            )
        )
        assert result == [
            (1, "path1", 100, "2013-01-01 12:00:00", "asd"),
            (2, "path2", 100, "2013-01-01 12:00:00", "qwe"),
        ]

        result = list(
            db.get_latest_many(
                [("path2", 100, "2013-01-01 12:00:00"), ("path1", 100, "2013-01-01 12:00:00")], 2, no={"entry_date"}
            )
        )
        assert result == [
            (2, "path2", 100, "2013-01-01 12:00:00", "qwe"),
            (1, "path1", 100, "2013-01-01 12:00:00", "asd"),
        ]

        sleep(2)
        db._add_row(("path3", 100, "2013-01-01 12:00:00"), derived={"data": "new"})

        result = list(
            db.get_latest_many(
                [("path1", 100, "2013-01-01 12:00:00"), ("path3", 100, "2013-01-01 12:00:00")], 2, no={"entry_date"}
            )
        )
        assert result == [
            (1, "path1", 100, "2013-01-01 12:00:00", "asd"),
            (4, "path3", 100, "2013-01-01 12:00:00", "new"),
        ]


if __name__ == "__main__":
    unittest.main()
