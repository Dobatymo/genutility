import hashlib
import json
import os
import shutil
import subprocess
import sys
import warnings
from importlib.util import find_spec
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from zipfile import ZipFile

try:
    from importlib.resources import files
except ImportError:
    from importlib_resources import files

from genutility.exceptions import ParseError
from genutility.fileformats.heif import NoExifFound, _read_extent, heif_get_exif
from genutility.fileformats.isobmff import BoxParser, FileSlice, _layout_is_plausible, enumerate_atoms
from genutility.test import MyTestCase

FIXTURES = files("testfiles").joinpath("mp4")
FFMPEG = FIXTURES / "ffmpeg"
DERIVED = FIXTURES / "ffmpeg-derived"
SYNTHETIC = FIXTURES / "synthetic"
MEDIA_SUFFIXES = {".mp4", ".mov", ".heic", ".heif", ".avif", ".m4a", ".m4v", ".3gp", ".3g2", ".mj2", ".mjp2"}


def normalize(value):
    """Represent bytes and tuple fields without losing scalar/sequence distinctions."""
    if isinstance(value, bytes):
        return {"hex": value.hex()}
    if isinstance(value, dict):
        return {key: normalize(val) for key, val in value.items()}
    if isinstance(value, (tuple, list)):
        return [normalize(val) for val in value]
    return value


def parser_result(path, options):
    """Read lazy payloads while their stream is open, including the prefix before an error."""
    atoms = []
    result = {}
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            for depth, position, code, size, content, leaf in enumerate_atoms(path, **options):
                payload = None
                if leaf is not None:
                    payload = {"offset": leaf.offset, "size": len(leaf), "hex": leaf.read().hex()}
                atoms.append([depth, position, code, size, normalize(content), payload])
        except Exception as exc:  # noqa: BLE001 - Unexpected exception classes must also fail the recorded expectation.
            result["error"] = {"type": type(exc).__name__, "match": str(exc)}
    # Large reference-chain fixtures exercise extraction limits, not thousands of repeated box records.
    if len(atoms) > 100:
        result["atom_count"] = len(atoms)
    else:
        result["atoms"] = atoms
    result["warnings"] = sorted({str(warning.message) for warning in caught})
    return result


class Mp4Test(MyTestCase):
    def test_zip_import_loads_atom_table(self):
        with TemporaryDirectory() as tempdir:
            archive = Path(tempdir) / "package.zip"
            pending = [(files("genutility"), "genutility")]
            with ZipFile(archive, "w") as zipped:
                while pending:
                    directory, prefix = pending.pop()
                    for resource in directory.iterdir():
                        name = f"{prefix}/{resource.name}"
                        if resource.is_dir() and resource.name != "__pycache__":
                            pending.append((resource, name))
                        elif resource.is_file() and resource.name.endswith((".py", ".tsv")):
                            zipped.writestr(name, resource.read_bytes())
            shutil.copyfile(FFMPEG / "minimal-isom.mp4", Path(tempdir) / "movie.mp4")
            result = subprocess.run(  # noqa: S603
                [
                    sys.executable,
                    "-B",
                    "-OO",
                    "-c",
                    (
                        "from genutility.fileformats import isobmff\n"
                        "import sys\n"
                        "if not isobmff.__spec__.origin.startswith(sys.argv[1]):\n"
                        "    raise RuntimeError('Package was not imported from ZIP')\n"
                        "if not any(atom[2] == 'av1C' for atom in isobmff.enumerate_atoms('movie.mp4', parse_atoms=True)):\n"
                        "    raise RuntimeError('Missing AV1 configuration box')\n"
                    ),
                    str(archive),
                ],
                cwd=tempdir,
                env={**os.environ, "PYTHONPATH": str(archive)},
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(0, result.returncode, result.stderr)

    def test_codec_sample_entry_children(self):
        for filename, entry, config, dimensions in (
            ("minimal-isom.mp4", "av01", "av1C", (1, 1)),
            ("minimal-hvc1.mp4", "hvc1", "hvcC", (16, 16)),
            ("minimal-hev1.mp4", "hev1", "hvcC", (16, 16)),
            ("minimal-avc3.mp4", "avc3", "avcC", (2, 2)),
            ("minimal-vp9.mp4", "vp09", "vpcC", (1, 1)),
            ("minimal-opus.mp4", "Opus", "dOps", None),
            ("minimal-flac.mp4", "fLaC", "dfLa", None),
            ("minimal-ac3.mp4", "ac-3", "dac3", None),
            ("minimal-eac3.mp4", "ec-3", "dec3", None),
        ):
            for parsed in (False, True):
                with self.subTest(file=filename, parsed=parsed):
                    result = parser_result(FFMPEG / filename, {"parse_atoms": parsed})
                    self.assertNotIn("error", result)
                    atoms = result["atoms"]
                    sample = next(atom for atom in atoms if atom[2] == entry)
                    configuration = next(atom for atom in atoms if atom[2] == config)
                    self.assertEqual(sample[0] + 1, configuration[0])
                    self.assertIsNone(sample[5])
                    self.assertIsNotNone(configuration[5])
                    if parsed:
                        self.assertEqual(1, sample[4]["data_reference_index"])
                        if dimensions is not None:
                            self.assertEqual(dimensions, (sample[4]["width"], sample[4]["height"]))
                        else:
                            self.assertEqual(48000 << 16, sample[4]["sample_rate_fixed"])

    def test_scheme_type_retains_raw_payload(self):
        for parsed in (False, True):
            with self.subTest(parsed=parsed):
                result = parser_result(FFMPEG / "minimal-cenc.mp4", {"parse_atoms": parsed})
                self.assertNotIn("error", result)
                scheme = next(atom for atom in result["atoms"] if atom[2] == "schm")
                self.assertIsNotNone(scheme[5])
                if parsed:
                    self.assertEqual({"scheme_type": {"hex": "63656e63"}, "scheme_version": 65536}, scheme[4])
                else:
                    self.assertEqual("63656e6300010000", scheme[5]["hex"])

    def test_unknown_box_types_preserve_following_boxes(self):
        for profile in ("auto", "isobmff"):
            for parsed in (False, True):
                with self.subTest(profile=profile, parsed=parsed):
                    result = parser_result(
                        DERIVED / "minimal-unknown-boxes.mp4", {"profile": profile, "parse_atoms": parsed}
                    )
                    self.assertNotIn("error", result)
                    tail = result["atoms"][-3:]
                    self.assertEqual(["\xa9xyz", "\0\1\2\3", "free"], [atom[2] for atom in tail])
                    self.assertEqual("4e455854", tail[-1][5]["hex"])
                    self.assertEqual(2, len(result["warnings"]))

    def test_structural_detection_only_without_ftyp(self):
        with patch("genutility.fileformats.isobmff._layout_is_plausible", side_effect=AssertionError("Used detection")):
            for filename, rejects in (
                ("ftyp-iso-empty-meta.mp4", False),
                ("ftyp-qt-empty-meta.mov", False),
                ("ftyp-compatible-quicktime.mp4", False),
                ("ftyp-late-quicktime.mov", False),
                ("ftyp-iso-wrong-meta.mp4", True),
                ("ftyp-qt-wrong-meta.mov", True),
                ("ftyp-short-after-free.mp4", True),
            ):
                for parsed in (False, True):
                    with self.subTest(file=filename, parse_atoms=parsed):
                        result = parser_result(SYNTHETIC / filename, {"profile": "auto", "parse_atoms": parsed})
                        self.assertEqual("ParseError" if rejects else None, result.get("error", {}).get("type"))
        with patch("genutility.fileformats.isobmff._layout_is_plausible", wraps=_layout_is_plausible) as detect:
            result = parser_result(SYNTHETIC / "mixed-meta-dialects-01.mov", {"profile": "auto", "parse_atoms": True})
            self.assertNotIn("error", result)
            self.assertGreater(detect.call_count, 0)

    def test_files(self):
        fixtures = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))
        self.assertTrue(fixtures)
        names = [fixture["file"] for fixture in fixtures]
        self.assertEqual(len(names), len(set(names)), "Duplicate fixture names")
        files = {
            path.relative_to(FIXTURES).as_posix()
            for path in FIXTURES.rglob("*")
            if path.is_file() and path.suffix.lower() in MEDIA_SUFFIXES
        }
        self.assertEqual(files, set(names), "Every fixture must have explicit expectations")

        for fixture in fixtures:
            path = FIXTURES / fixture["file"]
            with self.subTest(file=fixture["file"]):
                self.assertIn(path.parent.name, ("ffmpeg", "ffmpeg-derived", "synthetic", "regression"))
                self.assertEqual("fragment" if path.parent.name == "synthetic" else "media", fixture["kind"])
                self.assertEqual(fixture["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
                self.assertTrue(fixture["checks"])
            for check in fixture["checks"]:
                self.assertTrue(check["options"])
                for options in check["options"]:
                    with self.subTest(file=fixture["file"], **options):
                        self.assertEqual(check["expect"], parser_result(path, options))
            if "exif" in fixture:
                with self.subTest(file=fixture["file"], operation="extract-exif"), warnings.catch_warnings():
                    warnings.simplefilter("ignore", UserWarning)
                    expected = fixture["exif"]
                    if "error" in expected:
                        errors = {"ParseError": ParseError, "ValueError": ValueError, "NoExifFound": NoExifFound}
                        with self.assertRaises(errors[expected["error"]["type"]]) as error:
                            heif_get_exif(path)
                        self.assertEqual(expected["error"]["match"], str(error.exception))
                    else:
                        self.assertEqual(bytes.fromhex(expected["hex"]), heif_get_exif(path))

    def test_heif_shared_sources_are_read_once(self):
        with patch("genutility.fileformats.heif._read_extent", wraps=_read_extent) as read_extent:
            self.assertEqual(b"II*\0\x08\0\0\0" + b"\0" * 6, heif_get_exif(SYNTHETIC / "heif-shared-source-01.heic"))
            self.assertEqual(33, read_extent.call_count)

    def test_heif_cli_continues_after_errors(self):
        if find_spec("piexif") is None:
            self.skipTest("piexif not available")
        with TemporaryDirectory() as tempdir:
            for source, filename in (
                ("heif-cli-01.heic", "bad.heic"),
                ("heif-cli-02.heic", "bad-exif.heic"),
                ("heif-cli-03.heic", "valid.heic"),
                ("heif-reference-depth-04.heic", "deep.heic"),
            ):
                shutil.copyfile(SYNTHETIC / source, Path(tempdir) / filename)
            result = subprocess.run(  # noqa: S603
                [sys.executable, "-B", "-OO", "-m", "genutility.fileformats.heif", tempdir],
                capture_output=True,
                text=True,
                check=True,
            )
        self.assertIn("valid.heic", result.stdout)
        for text in ("bad.heic", "bad-exif.heic", "ParseError", "limit of 128"):
            self.assertIn(text, result.stderr)
        for text in ("KeyError", "RecursionError"):
            self.assertNotIn(text, result.stderr)

    def test_cli_errors_only_with_type_filter(self):
        if find_spec("rich") is None:
            self.skipTest("rich not available")
        for filename, atom_type, reports_error, error_message in (
            ("cli-truncated-header-01.mp4", "mdat", True, "Truncated atom header"),
            ("cli-truncated-header-02.mp4", "mdat", False, "Truncated atom header"),
            ("cli-truncated-header-02.mp4", "free", True, "Truncated atom header"),
            ("atom-depth-1100.mp4", "free", True, "Atom nesting exceeds the limit of 128"),
        ):
            with self.subTest(file=filename, atom_type=atom_type), TemporaryDirectory() as tempdir:
                shutil.copyfile(SYNTHETIC / filename, Path(tempdir) / "bad.mp4")
                result = subprocess.run(  # noqa: S603
                    [
                        sys.executable,
                        "-B",
                        "-OO",
                        "-m",
                        "genutility.fileformats.isobmff",
                        tempdir,
                        "--errors-only",
                        "--type",
                        atom_type,
                    ],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                self.assertIn("1/1 files failed" if reports_error else "0/1 files failed", result.stdout)
                self.assertEqual(reports_error, error_message in result.stderr)
                self.assertNotIn("RecursionError", result.stderr)

    def test_cli_discovers_iso_media_extensions(self):
        if find_spec("rich") is None:
            self.skipTest("rich not available")
        with TemporaryDirectory() as tempdir:
            for directory, filename in (
                (FFMPEG, "media-h263.3gp"),
                (FFMPEG, "media-mpeg4.3g2"),
                (DERIVED, "media-jpeg2000.mj2"),
                (SYNTHETIC, "sample-mj2-twos.mjp2"),
            ):
                shutil.copyfile(directory / filename, Path(tempdir) / filename)
            result = subprocess.run(  # noqa: S603
                [sys.executable, "-B", "-OO", "-m", "genutility.fileformats.isobmff", tempdir, "--errors-only"],
                capture_output=True,
                text=True,
                check=True,
            )
        self.assertIn("0/4 files failed", result.stdout)

    def test_box_parser_rejects_cstring_read_past_eof(self):
        with self.assertRaises(EOFError):
            BoxParser.read_c_string(BytesIO(b"unterminated"), 1000)

    def test_heif_extent_bounds_for_file_and_item_data(self):
        with BytesIO(b"PADabcdefTAIL") as stream:
            for source in (b"abcdef", FileSlice(stream, 3, 6)):
                with self.subTest(source=type(source).__name__):
                    self.assertEqual(b"cdef", _read_extent(source, 2, 0, 1))
                    for offset, length, extent_count in ((7, 1, 1), (5, 2, 1), (0, 0, 2)):
                        with self.subTest(offset=offset, length=length, extent_count=extent_count), self.assertRaises(
                            ValueError
                        ):
                            _read_extent(source, offset, length, extent_count)


if __name__ == "__main__":
    import unittest

    unittest.main()
