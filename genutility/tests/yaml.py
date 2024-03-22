from genutility._file import CloseableNamedTemporaryFile
from genutility.test import MyTestCase, parametrize
from genutility.yaml import read_yaml, write_yaml


class YamlTest(MyTestCase):
    @parametrize(("", None), ("null\n...\n", None), ("{asd: 1}\n", {"asd": 1}))
    def test_read_yaml(self, content, truth):
        with CloseableNamedTemporaryFile(mode="wt", encoding="utf-8") as (f, fname):
            f.write(content)
            f.flush()  # or f.close()
            result = read_yaml(fname)

        self.assertEqual(truth, result)

    @parametrize((None, "null\n...\n"), ({"asd": 1}, "{asd: 1}\n"))
    def test_write_yaml(self, content, truth):
        with CloseableNamedTemporaryFile(mode="w+t", encoding="utf-8") as (f, fname):
            write_yaml(content, fname)
            result = f.read()

        self.assertEqual(truth, result)


if __name__ == "__main__":
    import unittest

    unittest.main()
