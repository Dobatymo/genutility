from unittest import TestCase

from genutility.pyhash import py2_hash_ucs_4

vectors_64_UCS_4 = [
    ("", 0),
    (b"", 0),
    ("a", 12416037344),
    (b"a", 12416037344),
    ("asd", 1453079729203098327),
    (b"asd", 1453079729203098327),
    ("qwe", 1882935602998924874),
    (b"qwe", 1882935602998924874),
    ("你好", 2600975626103484255),  # UCS_4 specific
    (b"\xe4\xbd\xa0\xe5\xa5\xbd", -1518367109890466456),
    ("ありがとう", 3383731150270177651),  # UCS_4 specific
    (b"\xe3\x81\x82\xe3\x82\x8a\xe3\x81\x8c\xe3\x81\xa8\xe3\x81\x86", -3506057757780959018),
    ("resumé", 1339948677000479307),
    (b"resum\xc3\xa9", -345923677783396773),
]

vectors_32_UCS_4 = [
    ("", 0),
    (b"", 0),
    ("a", -468864544),
    (b"a", -468864544),
    ("asd", -1585925417),
    (b"asd", -1585925417),
    ("qwe", 1739576906),
    (b"qwe", 1739576906),
    # (u"你好", -1759270464),  # UCS_2
    ("你好", 660139871),  # UCS_4
    (b"\xe4\xbd\xa0\xe5\xa5\xbd", -2141741720),
    # (u"ありがとう", -294469882),  # UCS_2
    ("ありがとう", -1421401741),  # UCS_4
    (b"\xe3\x81\x82\xe3\x82\x8a\xe3\x81\x8c\xe3\x81\xa8\xe3\x81\x86", -1854496554),
    ("resumé", -304201141),
    (b"resum\xc3\xa9", 1918037595),
]


class HashTest(TestCase):
    def test_hash_32(self):
        for data, truth in vectors_32_UCS_4:
            result = py2_hash_ucs_4(data, 32)
            assert truth == result, (data, truth, result)

    def test_hash_64(self):
        for data, truth in vectors_64_UCS_4:
            result = py2_hash_ucs_4(data, 64)
            assert truth == result, (data, truth, result)


if __name__ == "__main__":
    import unittest

    unittest.main()
