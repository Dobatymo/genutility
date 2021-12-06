from __future__ import generator_stop

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


class HistoryDBTest(MyTestCase):
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


if __name__ == "__main__":
    import unittest

    unittest.main()
