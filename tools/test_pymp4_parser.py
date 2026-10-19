"""Run with `python -m unittest tools.test_pymp4_parser` in the pymp4 environment."""

import unittest
from pathlib import Path

from tools.pymp4_parser import parse_file


class Pymp4WorkerTest(unittest.TestCase):
    def test_reads_all_top_level_boxes_and_reports_bad_suffix(self):
        corpus = Path("testfiles/mp4")
        path = corpus / "ffmpeg" / "media-mpeg4.3g2"
        accepted = parse_file(path)
        self.assertNotIn("error", accepted)
        self.assertGreaterEqual(len(accepted["boxes"]), 2)
        self.assertEqual(path.stat().st_size, accepted["consumed_bytes"])

        path = corpus / "synthetic" / "invalid-trailing-short-header.mp4"
        rejected = parse_file(path)
        self.assertIn("error", rejected)
        self.assertEqual(1, len(rejected["boxes"]))
        self.assertEqual(path.stat().st_size, rejected["file_bytes"])


if __name__ == "__main__":
    unittest.main()
