from pathlib import Path
from tempfile import TemporaryDirectory

from genutility.fileformats.mp4 import atoms, enumerate_atoms
from genutility.test import MyTestCase


class Mp4Test(MyTestCase):
    def test_atoms_loaded(self):
        self.assertEqual(("leaf", "box", "File type"), atoms["ftyp"])

    def test_enumerate_minimal_ftyp(self):
        with TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "minimal.mp4"
            path.write_bytes(b"\x00\x00\x00\x10ftypisom\x00\x00\x00\x00")

            result = list(enumerate_atoms(str(path), parse_atoms=True))

        truth = [(0, 0, "ftyp", 16, {"major_brand": b"isom", "minor_version": 0}, None)]
        self.assertEqual(truth, result)


if __name__ == "__main__":
    import unittest

    unittest.main()
