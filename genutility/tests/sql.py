from genutility.sql import convert_mysql_to_sqlite
from genutility.test import MyTestCase, parametrize


class SqlTest(MyTestCase):
    @parametrize(
        ("", ""),
        ("asd", "asd"),
        ("x\\'x", "x''x"),
        ("x\\\\x", "x\\x"),
        ("x\\\\'x", "x\\'x"),
        ("x\\'x\\\\x\\\\'x", "x''x\\x\\'x"),
    )
    def test_convert_mysql_to_sqlite(self, s, truth):
        result = convert_mysql_to_sqlite(s)
        self.assertEqual(truth, result)


if __name__ == "__main__":
    import unittest

    unittest.main()
