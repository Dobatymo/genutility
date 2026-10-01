import json
import stat
from argparse import ArgumentTypeError
from datetime import datetime, timezone
from inspect import signature
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from genutility.args import (
    base32_bytes,
    base32_str,
    base64_bytes,
    base64_str,
    byte_size_iec,
    byte_size_si,
    datetime_iso,
    empty_dir,
    empty_dir_nofollow,
    encoding_name,
    existing_path,
    existing_path_nofollow,
    finite_float,
    future_file,
    hex_bytes,
    int_at_least,
    is_dir,
    is_dir_nofollow,
    is_file,
    is_file_nofollow,
    is_file_or_dir,
    is_file_or_dir_nofollow,
    json_file,
    json_file_nofollow,
    multiple_of,
    new_path,
    non_negative_float,
    non_negative_int,
    path_nofollow,
    positive_float,
    positive_int,
    relative_path,
)


class ArgsTest(TestCase):
    def test_datetime_iso(self):
        self.assertEqual(datetime.fromisoformat("2026-08-01T00"), datetime_iso("2026-08-01T00"))
        self.assertEqual(datetime.fromisoformat("2026-08-01T00:30"), datetime_iso("2026-08-01T00:30"))
        self.assertEqual(
            datetime(2026, 8, 1, 0, 30, tzinfo=timezone.utc),
            datetime_iso("2026-08-01T00:30Z"),
        )
        with self.assertRaises(ArgumentTypeError):
            datetime_iso("not-a-datetime")

    def test_path_types(self):
        with TemporaryDirectory() as tmpdirname:
            root = Path(tmpdirname)
            file = root / "file.json"
            file.write_text(json.dumps({"value": 1}), encoding="utf-8")
            directory = root / "directory"
            directory.mkdir()
            missing = root / "missing"

            self.assertEqual(file, existing_path(file))
            self.assertEqual(file, existing_path_nofollow(file))
            self.assertEqual(file, is_file(file))
            self.assertEqual(file, is_file_nofollow(file))
            self.assertEqual(file, is_file_or_dir(file))
            self.assertEqual(file, is_file_or_dir_nofollow(file))
            self.assertEqual(directory, is_dir(directory))
            self.assertEqual(directory, is_dir_nofollow(directory))
            self.assertEqual(directory, is_file_or_dir(directory))
            self.assertEqual(directory, is_file_or_dir_nofollow(directory))
            self.assertEqual(file, path_nofollow(file))
            self.assertEqual(directory, path_nofollow(directory))
            self.assertEqual(missing, path_nofollow(missing))
            self.assertEqual(missing, new_path(missing))
            self.assertEqual({"value": 1}, json_file(file))
            self.assertEqual({"value": 1}, json_file_nofollow(file))
            self.assertEqual(directory, empty_dir(directory))
            self.assertEqual(directory, empty_dir_nofollow(directory))

            for parser, value in (
                (existing_path, missing),
                (is_file, directory),
                (is_file, missing),
                (is_file_or_dir, missing),
                (is_file_or_dir_nofollow, missing),
                (is_dir, file),
                (is_dir, missing),
                (new_path, file),
                (empty_dir, file),
                (empty_dir, missing),
                (json_file, directory),
                (json_file, missing),
            ):
                with self.subTest(parser=parser.__name__, value=value), self.assertRaises(ArgumentTypeError):
                    parser(value)

            (directory / "entry").write_text("x", encoding="utf-8")
            with self.assertRaises(ArgumentTypeError):
                empty_dir(directory)

            bad_json = root / "bad.json"
            bad_json.write_text("{", encoding="utf-8")
            with self.assertRaises(ArgumentTypeError):
                json_file(bad_json)

            with self.assertRaises(ArgumentTypeError):
                future_file(root / "missing-parent" / "file")

    def test_link_policy(self):
        with TemporaryDirectory() as tmpdirname:
            root = Path(tmpdirname)
            target = root / "target"
            target.write_text(json.dumps({"value": 1}), encoding="utf-8")
            link = root / "link"
            target_dir = root / "target-dir"
            target_dir.mkdir()
            dir_link = root / "dir-link"
            try:
                link.symlink_to(target)
                dir_link.symlink_to(target_dir, target_is_directory=True)
            except OSError as e:
                self.skipTest(f"cannot create symbolic link: {e}")

            self.assertEqual(link, existing_path(link))
            with self.assertRaises(ArgumentTypeError):
                existing_path_nofollow(link)
            self.assertEqual(link, is_file(link))
            self.assertEqual(link, is_file_or_dir(link))
            with self.assertRaises(ArgumentTypeError):
                is_file_nofollow(link)
            with self.assertRaises(ArgumentTypeError):
                is_file_or_dir_nofollow(link)
            with self.assertRaises(ArgumentTypeError):
                path_nofollow(link)

            for parser in (existing_path, is_dir, is_file_or_dir, empty_dir):
                with self.subTest(parser=parser.__name__):
                    self.assertEqual(dir_link, parser(dir_link))

            for parser in (
                existing_path_nofollow,
                is_dir_nofollow,
                is_file_or_dir_nofollow,
                path_nofollow,
                empty_dir_nofollow,
            ):
                with self.subTest(parser=parser.__name__), self.assertRaises(ArgumentTypeError):
                    parser(dir_link)

            self.assertEqual({"value": 1}, json_file(link))
            with self.assertRaises(ArgumentTypeError):
                json_file_nofollow(link)

            with self.assertRaises(ArgumentTypeError):
                new_path(link)
            with self.assertRaises(ArgumentTypeError):
                future_file(link)

            broken = root / "broken"
            broken.symlink_to(root / "does-not-exist")
            for parser in (
                existing_path,
                existing_path_nofollow,
                is_file,
                is_file_nofollow,
                is_file_or_dir,
                is_file_or_dir_nofollow,
            ):
                with self.subTest(parser=parser.__name__, broken=True), self.assertRaises(ArgumentTypeError):
                    parser(broken)
            with self.assertRaises(ArgumentTypeError):
                new_path(broken)
            with self.assertRaises(ArgumentTypeError):
                path_nofollow(broken)

    def test_path_transformations(self):
        relative = Path("relative")
        self.assertEqual(relative, relative_path(relative))
        with self.assertRaises(ArgumentTypeError):
            relative_path(relative.absolute())

    def test_path_types_accept_one_argument(self):
        for parser in (
            existing_path,
            existing_path_nofollow,
            is_dir,
            is_dir_nofollow,
            is_file,
            is_file_nofollow,
            is_file_or_dir,
            is_file_or_dir_nofollow,
            path_nofollow,
            new_path,
            future_file,
            empty_dir,
            empty_dir_nofollow,
            json_file,
            json_file_nofollow,
            relative_path,
        ):
            with self.subTest(parser=parser.__name__):
                self.assertEqual(1, len(signature(parser).parameters))

    def test_windows_reparse_point_policy(self):
        fake_stat = SimpleNamespace(st_mode=stat.S_IFDIR)
        with patch("genutility.args.os.stat", return_value=fake_stat), patch(
            "genutility.args.islink", return_value=True
        ):
            self.assertEqual(Path("reparse"), existing_path("reparse"))
            self.assertEqual(Path("reparse"), is_file_or_dir("reparse"))
            with self.assertRaises(ArgumentTypeError):
                existing_path_nofollow("reparse")
            with self.assertRaises(ArgumentTypeError):
                is_file_or_dir_nofollow("reparse")
            with self.assertRaises(ArgumentTypeError):
                path_nofollow("reparse")

        file_stat = SimpleNamespace(st_mode=stat.S_IFREG)
        with patch("genutility.args.os.stat", return_value=file_stat), patch(
            "genutility.args.islink", return_value=True
        ):
            self.assertEqual(Path("reparse"), is_file("reparse"))
            self.assertEqual(Path("reparse"), is_file_or_dir("reparse"))
            with self.assertRaises(ArgumentTypeError):
                is_file_nofollow("reparse")
            with self.assertRaises(ArgumentTypeError):
                is_file_or_dir_nofollow("reparse")

        other_stat = SimpleNamespace(st_mode=stat.S_IFIFO)
        with patch("genutility.args.os.stat", return_value=other_stat), patch(
            "genutility.args.islink", return_value=False
        ):
            with self.assertRaises(ArgumentTypeError):
                is_file_or_dir("other")
            with self.assertRaises(ArgumentTypeError):
                is_file_or_dir_nofollow("other")

    def test_binary_encodings(self):
        self.assertEqual(b"foo", base64_bytes("Zm9v"))
        self.assertEqual(b"", base64_bytes(""))
        self.assertEqual("Zm9v", base64_str("Zm9v"))
        self.assertEqual("", base64_str(""))

        self.assertEqual(b"foo", base32_bytes("MZXW6==="))
        self.assertEqual(b"foo", base32_bytes("mzxw6==="))
        self.assertEqual(b"", base32_bytes(""))
        self.assertEqual("MZXW6===", base32_str("MZXW6==="))
        self.assertEqual("mzxw6===", base32_str("mzxw6==="))
        self.assertEqual("", base32_str(""))

        for parser in (base64_bytes, base64_str, base32_bytes, base32_str):
            for value in ("!!!!", "\N{LATIN SMALL LETTER A WITH DIAERESIS}"):
                with self.subTest(parser=parser.__name__, value=value), self.assertRaises(ArgumentTypeError):
                    parser(value)

    def test_hex_bytes(self):
        parser = hex_bytes(2)

        self.assertEqual(b"\x00\xff", parser("00fF"))
        for value in ("", "0", "000", "00000", "00 ff", "00fg", "\N{ARABIC-INDIC DIGIT ZERO}" * 4):
            with self.subTest(value=value), self.assertRaises(ArgumentTypeError):
                parser(value)
        with self.assertRaises(ValueError):
            hex_bytes(-1)

    def test_byte_sizes(self):
        for parser, base in ((byte_size_si, 1000), (byte_size_iec, 1024)):
            with self.subTest(base=base):
                self.assertEqual(0, parser("0"))
                for exponent, suffix in enumerate("KMGTPEZY", 1):
                    self.assertEqual(2 * base**exponent, parser(f"2{suffix}"))

                for value in (
                    "",
                    "-1",
                    "+1",
                    "1.0",
                    " 1K",
                    "1 K",
                    "1K ",
                    "1B",
                    "1b",
                    "1KB",
                    "1Ki",
                    "1k",
                    "1R",
                    "1_000",
                    "١K",  # noqa: RUF001
                    "K",
                ):
                    with self.subTest(base=base, value=value), self.assertRaises(ArgumentTypeError) as cm:
                        parser(value)
                    self.assertIn(str(base), str(cm.exception))

    def test_int_bounds(self):
        self.assertEqual(0, non_negative_int("0"))
        self.assertEqual(1, positive_int("1"))
        self.assertEqual(-1, int_at_least(-1)("-1"))

        with self.assertRaises(ArgumentTypeError):
            non_negative_int("-1")
        with self.assertRaises(ArgumentTypeError):
            positive_int("0")
        with self.assertRaises(ArgumentTypeError):
            int_at_least(-1)("-2")

    def test_finite_float_bounds(self):
        self.assertEqual(-1.5, finite_float("-1.5"))
        self.assertEqual(0.0, non_negative_float("0"))
        self.assertEqual(0.5, positive_float("0.5"))

        for value in ("nan", "inf", "-inf"):
            with self.subTest(value=value), self.assertRaises(ArgumentTypeError):
                finite_float(value)
        with self.assertRaises(ArgumentTypeError):
            non_negative_float("-0.5")
        with self.assertRaises(ArgumentTypeError):
            positive_float("0")

    def test_encoding_name(self):
        self.assertEqual("utf-8", encoding_name("utf-8"))

        with self.assertRaises(ArgumentTypeError):
            encoding_name("not-an-encoding")

    def test_multiple_of_with_minimum(self):
        block_size = multiple_of(512, minimum=0)

        self.assertEqual(0, block_size("0"))
        self.assertEqual(1024, block_size("1024"))
        with self.assertRaises(ArgumentTypeError):
            block_size("-512")
        with self.assertRaises(ArgumentTypeError):
            block_size("513")
        with self.assertRaises(ValueError):
            multiple_of(0)
