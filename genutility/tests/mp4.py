import struct
from pathlib import Path
from tempfile import TemporaryDirectory

from genutility.exceptions import ParseError
from genutility.fileformats.mp4 import _atom_definition, enumerate_atoms
from genutility.test import MyTestCase


class Mp4Test(MyTestCase):
    def test_atoms_loaded(self):
        definition = _atom_definition("ftyp", "isobmff", None)
        self.assertEqual(("payload", "box", "File type"), (definition.grammar, definition.boxtype, definition.description))

    def test_atom_definitions_support_profile_and_parent_variants(self):
        self.assertEqual("fullbox", _atom_definition("meta", "isobmff", None).boxtype)
        self.assertEqual("box", _atom_definition("meta", "quicktime", None).boxtype)
        self.assertEqual("box", _atom_definition("data", "quicktime", "ilst").boxtype)
        frma = _atom_definition("frma", "isobmff", "sinf")
        saio = _atom_definition("saio", "isobmff", "traf")
        self.assertEqual(("payload", "box"), (frma.grammar, frma.boxtype))
        self.assertEqual(("payload", "fullbox"), (saio.grammar, saio.boxtype))
        self.assertEqual("box", _atom_definition("text", "auto", "gmhd").boxtype)
        self.assertEqual("box", _atom_definition("thmb", "auto", "tref").boxtype)
        self.assertIsNone(_atom_definition("data", "isobmff", "ilst"))
        self.assertEqual("item-list", _atom_definition("ilst", "isobmff", "meta").grammar)
        self.assertEqual("sample-entry:visual", _atom_definition("avc1", "isobmff", "stsd").grammar)

    def test_sample_entry_grammar_is_table_driven(self):
        esds = struct.pack(">L4s4B", 12, b"esds", 0, 0, 0, 0)
        srat = struct.pack(">L4s4BL", 16, b"srat", 0, 0, 0, 0, 48000)
        cases = (
            ("isobmff", 0, 0, 28, esds),
            ("isobmff", 1, 1, 28, srat),
            ("quicktime", 0, 1, 44, esds),
            ("quicktime", 0, 2, 64, esds),
        )

        with TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "sample-entry.mp4"
            for profile, stsd_version, audio_version, prefix_size, child in cases:
                prefix = b"\0" * 8 + struct.pack(">H", audio_version) + b"\0" * (prefix_size - 10)
                mp4a = struct.pack(">L4s", 8 + len(prefix) + len(child), b"mp4a") + prefix + child
                body = struct.pack(">B3sL", stsd_version, b"\0" * 3, 1) + mp4a
                path.write_bytes(struct.pack(">L4s", 8 + len(body), b"stsd") + body)

                for parse_atoms in (False, True):
                    with self.subTest(parse_atoms=parse_atoms, profile=profile, stsd_version=stsd_version):
                        result = list(enumerate_atoms(str(path), parse_atoms=parse_atoms, profile=profile))
                        self.assertEqual(["stsd", "mp4a", child[4:8].decode("ascii")], [entry[2] for entry in result])

    def test_sidx_and_mfro_are_leaf_boxes(self):
        sidx = struct.pack(">L4s4B4LHH", 44, b"sidx", 0, 0, 0, 0, 1, 1000, 0, 0, 0, 1)
        sidx += struct.pack(">3L", 1024, 1000, 0)
        mfro = struct.pack(">L4s4BL", 16, b"mfro", 0, 0, 0, 0, 24)
        mfra = struct.pack(">L4s", 24, b"mfra") + mfro

        with TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "index.mp4"
            for data, truth in ((sidx, ["sidx"]), (mfra, ["mfra", "mfro"])):
                path.write_bytes(data)
                with self.subTest(truth=truth):
                    result = list(enumerate_atoms(str(path), profile="isobmff"))
                self.assertEqual(truth, [entry[2] for entry in result])

    def test_unknown_container_header_is_probed_generically(self):
        child = struct.pack(">L4s", 8, b"free")

        with TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "unknown-header.mp4"
            for fullbox in (False, True):
                body = (b"\0\0\0\0" if fullbox else b"") + child
                path.write_bytes(struct.pack(">L4s", 8 + len(body), b"jp2h") + body)
                result = list(enumerate_atoms(str(path), profile="isobmff"))
                self.assertEqual(["jp2h", "free"], [entry[2] for entry in result])

    def test_enumerate_minimal_ftyp(self):
        with TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "minimal.mp4"
            path.write_bytes(b"\x00\x00\x00\x10ftypisom\x00\x00\x00\x00")

            result = list(enumerate_atoms(str(path), parse_atoms=True))

        truth = [(0, 0, "ftyp", 16, {"major_brand": b"isom", "minor_version": 0}, None)]
        self.assertEqual(truth, result)

    def test_tfdt_value(self):
        with TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "fragment.mp4"
            path.write_bytes(struct.pack(">L4s4BL", 16, b"tfdt", 0, 0, 0, 0, 5))

            result = list(enumerate_atoms(str(path), parse_atoms=True, profile="isobmff"))

        self.assertEqual({"baseMediaDecodeTime": 5}, result[0][4])

    def test_auto_detects_both_meta_variants(self):
        free = struct.pack(">L4s", 8, b"free")
        iso_meta = struct.pack(">L4s", 20, b"meta") + b"\0\0\0\0" + free
        quicktime_meta = struct.pack(">L4s", 16, b"meta") + free

        with TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "mixed.mov"
            path.write_bytes(iso_meta + quicktime_meta)

            result = list(enumerate_atoms(str(path), parse_atoms=True))

        self.assertEqual(["meta", "free", "meta", "free"], [entry[2] for entry in result])
        self.assertEqual([0, 1, 0, 1], [entry[0] for entry in result])

    def test_auto_rejects_unidentifiable_meta(self):
        with TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "ambiguous.mp4"
            path.write_bytes(struct.pack(">L4s", 8, b"meta"))

            with self.assertRaises(ParseError):
                list(enumerate_atoms(str(path)))

    def test_quicktime_artwork_fixture(self):
        path = Path(__file__).parents[2] / "testfiles" / "video" / "com.apple.quicktime.artwork.mp4"
        if not path.exists():
            self.skipTest("QuickTime fixture not available")

        result = list(enumerate_atoms(str(path), parse_atoms=True))

        self.assertEqual("mdat", result[-1][2])

    def test_quicktime_ilst_and_fourcc(self):
        item = struct.pack(">L4s", 8, b"\xa9nam")
        ilst = struct.pack(">L4s", 16, b"ilst") + item

        with TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "metadata.mov"
            path.write_bytes(ilst)

            result = list(enumerate_atoms(str(path), parse_atoms=True, profile="quicktime"))

        self.assertEqual(["ilst", "\xa9nam"], [entry[2] for entry in result])
        self.assertEqual([0, 1], [entry[0] for entry in result])

    def test_quicktime_numeric_atom_type(self):
        numeric_type = bytes.fromhex("00000001")
        atom = struct.pack(">L4s", 8, numeric_type)

        with TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "numeric.mov"
            path.write_bytes(atom)

            for profile in ("auto", "quicktime"):
                with self.subTest(profile=profile), self.assertWarns(UserWarning):
                    result = list(enumerate_atoms(str(path), profile=profile))
                self.assertEqual(numeric_type.decode("latin-1"), result[0][2])

            with self.assertRaises(ParseError):
                list(enumerate_atoms(str(path), profile="isobmff"))

            ilst = struct.pack(">L4s", 16, b"ilst") + atom
            path.write_bytes(ilst)
            result = list(enumerate_atoms(str(path), profile="quicktime"))
            self.assertEqual("1", result[1][2])

    def test_isobmff_ilst_container(self):
        item = struct.pack(">L4s", 16, b"name") + struct.pack(">L4s", 8, b"data")
        ilst = struct.pack(">L4s", 24, b"ilst") + item

        with TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "metadata.mp4"
            path.write_bytes(ilst)

            result = list(enumerate_atoms(str(path), profile="isobmff"))

        self.assertEqual(["ilst", "name", "data"], [entry[2] for entry in result])

    def test_invalid_profile(self):
        with TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "empty.mp4"
            path.write_bytes(b"")

            with self.assertRaises(ValueError):
                list(enumerate_atoms(str(path), profile="invalid"))

    def test_nested_zero_sized_atom_is_invalid(self):
        child = struct.pack(">L4s", 0, b"free")
        parent = struct.pack(">L4s", 16, b"moov") + child

        with TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "nested-zero.mp4"
            path.write_bytes(parent)

            with self.assertRaises(ParseError):
                list(enumerate_atoms(str(path)))

    def test_unsupported_version_is_invalid_under_optimization(self):
        atom = struct.pack(">L4s4BL", 16, b"stco", 1, 0, 0, 0, 0)

        with TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "unsupported-version.mp4"
            path.write_bytes(atom)

            with self.assertRaises(ParseError):
                list(enumerate_atoms(str(path), parse_atoms=True, profile="isobmff"))

    def test_no_parse_skips_dref_fields(self):
        url = struct.pack(">L4s4B", 12, b"url ", 0, 0, 0, 1)
        dref = struct.pack(">L4s4BL", 28, b"dref", 0, 0, 0, 0, 1) + url

        with TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "references.mp4"
            path.write_bytes(dref)

            result = list(enumerate_atoms(str(path)))

        self.assertEqual(["dref", "url "], [entry[2] for entry in result])
        self.assertEqual([0, 1], [entry[0] for entry in result])

    def test_iloc_zero_sized_fields(self):
        body = b"\0\0\0\0" + b"\0\0" + struct.pack(">HHHH", 1, 1, 0, 1)
        atom = struct.pack(">L4s", 8 + len(body), b"iloc") + body

        with TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "items.heif"
            path.write_bytes(atom)

            result = list(enumerate_atoms(str(path), parse_atoms=True, profile="isobmff"))

        item = result[0][4]["items"][0]
        self.assertEqual(1, item["item_ID"])
        self.assertEqual(0, item["base_offset"])
        self.assertEqual((0, 0), item["entries"][0])


if __name__ == "__main__":
    import unittest

    unittest.main()
