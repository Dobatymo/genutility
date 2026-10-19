"""Run with `python -m unittest tools.test_compare_mp4_parsers`."""

import json
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


class CompareMp4ParsersTest(unittest.TestCase):
    def test_external_parser_failures_and_portable_diagnostics(self):
        from tools.compare_mp4_parsers import run_parser

        with TemporaryDirectory() as tempdir:
            directory = Path(tempdir).resolve()
            escaped = json.dumps(str(directory))[1:-1]
            stdout = f"{directory}/file.mp4\n{directory.as_posix()}/file.mp4\n{escaped}\\\\file.mp4"
            outcomes = (
                subprocess.CompletedProcess(["parser"], 0, stdout, ""),
                subprocess.CompletedProcess(["parser"], 1, "", "bad input"),
                subprocess.TimeoutExpired(["parser"], 1),
                OSError("unavailable"),
            )
            with patch("tools.compare_mp4_parsers.subprocess.run", side_effect=outcomes) as run:
                results = [run_parser(["parser"], 1, directory) for _ in outcomes]
            self.assertEqual(["accept", "reject", "timeout", "unavailable"], [result["status"] for result in results])
            self.assertEqual(3, results[0]["stdout"].count("<INPUT_ROOT>"))
            self.assertNotIn(str(directory), results[0]["stdout"])
            self.assertEqual("bad input", results[1]["stderr"])
            self.assertEqual(4, run.call_count)


if __name__ == "__main__":
    unittest.main()
