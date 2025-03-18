import hashlib
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

try:
    # `"md4" not in hashlib.algorithms_available` seems not to work very consistently
    # https://github.com/python/cpython/issues/91257
    hashlib.new("md4")  # nosec: B324
except ValueError:
    MD4_NOT_AVAILABLE = True
else:
    MD4_NOT_AVAILABLE = False


class HashTest(MyTestCase):
    @classmethod
    def setUpClass(cls):
        data = b"abcdefghijklmnopqrstuvwxyz"
        write_file(data, "testtemp/hash.bin", "wb")
        write_file(bytearray(islice(cycle(data), ed2k_chunksize)), "testtemp/hash-ed2k-chunk.bin", "wb")

        write_file(b"", "testtemp/empty.bin", "wb")

    @parametrize(
        (crc32_hash_file, "testtemp/empty.bin", "00000000"),
        (crc32_hash_file, "testtemp/hash.bin", "4c2750bd"),
        (sha1_hash_file, "testtemp/empty.bin", "da39a3ee5e6b4b0d3255bfef95601890afd80709"),  # pragma: allowlist secret
        (sha1_hash_file, "testtemp/hash.bin", "32d10c7b8cf96570ca04ce37f2a19d84240d3a89"),  # pragma: allowlist secret
        (md5_hash_file, "testtemp/empty.bin", "d41d8cd98f00b204e9800998ecf8427e"),  # pragma: allowlist secret
        (md5_hash_file, "testtemp/hash.bin", "c3fcd3d76192e4007dfb496cca67e13b"),  # pragma: allowlist secret
    )
    def test_hash_file_empty(self, hashfunc, path, truth):
        result = hashfunc(path).hexdigest()
        self.assertEqual(truth, result)

    @skipIf(MD4_NOT_AVAILABLE, "hashlib built without md4")
    @parametrize(
        (Path("testtemp/hash.bin"), "d79e1c308aa5bbcdeea8ed63df412da9"),  # pragma: allowlist secret
    )
    def test_hash_file_v1v2(self, path, truth):
        result = ed2k_hash_file_v1(path)
        self.assertEqual(truth, result)

        result = ed2k_hash_file_v2(path)
        self.assertEqual(truth, result)

    @skipIf(MD4_NOT_AVAILABLE, "hashlib built without md4")
    @parametrize(
        (Path("testtemp/hash-ed2k-chunk.bin"), "5971de2e3a4dd3f2ed548da9c87c4491"),  # pragma: allowlist secret
    )
    def test_hash_file_v1(self, path, truth):
        result = ed2k_hash_file_v1(path)
        self.assertEqual(truth, result)

    @skipIf(MD4_NOT_AVAILABLE, "hashlib built without md4")
    @parametrize(
        (Path("testtemp/hash-ed2k-chunk.bin"), "621ed031c896a06e0dbc2c83df1ff9ea"),  # pragma: allowlist secret
    )
    def test_hash_file_v2(self, path, truth):
        result = ed2k_hash_file_v2(path)
        self.assertEqual(truth, result)


if __name__ == "__main__":
    import unittest

    unittest.main()
