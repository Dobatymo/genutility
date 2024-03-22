from hashlib import algorithms_available
from itertools import cycle, islice
from pathlib import Path
from unittest import skipIf

from genutility.file import write_file
from genutility.hash import (
    crc32_hash_file,
    ed2k_chunksize,
    ed2k_hash_file_v1,
    ed2k_hash_file_v2,
    md5_hash_file,
    sha1_hash_file,
)
from genutility.test import MyTestCase, parametrize


class HashTest(MyTestCase):
    @classmethod
    def setUpClass(cls):
        data = b"abcdefghijklmnopqrstuvwxyz"
        write_file(data, "testtemp/hash.bin", "wb")
        write_file(bytearray(islice(cycle(data), ed2k_chunksize)), "testtemp/hash-ed2k-chunk.bin", "wb")

    @parametrize(
        ("testtemp/hash.bin", "4c2750bd"),
    )
    def test_crc32_hash_file(self, path, truth):
        result = crc32_hash_file(path)
        self.assertEqual(truth, result)

    @parametrize(
        ("testtemp/hash.bin", "32d10c7b8cf96570ca04ce37f2a19d84240d3a89"),  # pragma: allowlist secret
    )
    def test_sha1_hash_file(self, path, truth):
        result = sha1_hash_file(path).hexdigest()
        self.assertEqual(truth, result)

    @parametrize(
        ("testtemp/hash.bin", "c3fcd3d76192e4007dfb496cca67e13b"),  # pragma: allowlist secret
    )
    def test_md5_hash_file(self, path, truth):
        result = md5_hash_file(path).hexdigest()
        self.assertEqual(truth, result)

    @skipIf("md4" not in algorithms_available, "hashlib built without md4")
    @parametrize(
        (Path("testtemp/hash.bin"), "d79e1c308aa5bbcdeea8ed63df412da9"),  # pragma: allowlist secret
    )
    def test_hash_file_v1v2(self, path, truth):
        result = ed2k_hash_file_v1(path)
        self.assertEqual(truth, result)

        result = ed2k_hash_file_v2(path)
        self.assertEqual(truth, result)

    @skipIf("md4" not in algorithms_available, "hashlib built without md4")
    @parametrize(
        (Path("testtemp/hash-ed2k-chunk.bin"), "5971de2e3a4dd3f2ed548da9c87c4491"),  # pragma: allowlist secret
    )
    def test_hash_file_v1(self, path, truth):
        result = ed2k_hash_file_v1(path)
        self.assertEqual(truth, result)

    @skipIf("md4" not in algorithms_available, "hashlib built without md4")
    @parametrize(
        (Path("testtemp/hash-ed2k-chunk.bin"), "621ed031c896a06e0dbc2c83df1ff9ea"),  # pragma: allowlist secret
    )
    def test_hash_file_v2(self, path, truth):
        result = ed2k_hash_file_v2(path)
        self.assertEqual(truth, result)


if __name__ == "__main__":
    import unittest

    unittest.main()
