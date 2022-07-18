from __future__ import generator_stop

from genutility.casedict import CaseDict
from genutility.test import MyTestCase


class CaseDictTest(MyTestCase):
    def test_all(self):

        cd = CaseDict()
        cd["ASD"] = 1
        cd["asd"] = 2
        self.assertEqual({"asd", "ASD"}, cd.igetitemset("Asd"))
        self.assertEqual({"ASD": 1, "asd": 2}, cd.igetitem("Asd"))

        self.assertEqual(set(), cd.igetset("qwe"))
        self.assertEqual({}, cd.iget("qwe"))


if __name__ == "__main__":
    import unittest

    unittest.main()
