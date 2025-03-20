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

    from genutility.polars import pl_index

from genutility.test import MyTestCase


class PolarsTest(MyTestCase):
    @skipIf(OLD_POLARS, "polars<1.18 or not installed")
    def test_pl_index(self):
        s = list("abcdefghij")
        df = pl.DataFrame({"a": s})
        ind = np.array([1, 3, 8])
        result = pl_index(df, ind)
        truth = pl.DataFrame({"a": ["b", "d", "i"]})
        self.assertTrue(truth.equals(result))


if __name__ == "__main__":
    import unittest

    unittest.main()
