"""Compare fixtures with genutility, FFmpeg/FFprobe and pymp4 (Python 3.8+)."""

import argparse
import json
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from genutility.tests.mp4 import MEDIA_SUFFIXES, parser_result

PROJECT_ROOT = Path.cwd()


def run_parser(command, timeout, directory):
    """Keep tool failures and timeouts as per-file results so the corpus scan continues."""
    try:
        result = subprocess.run(  # noqa: S603
            command,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"status": "timeout"}
    except OSError as exc:
        return {"status": "unavailable", "error": str(exc)}

    # FFprobe's JSON escapes Windows path separators; diagnostics may use either spelling.
    def portable(value):
        for prefix in (json.dumps(str(directory))[1:-1], str(directory), directory.as_posix()):
            value = value.replace(prefix, "<INPUT_ROOT>")
        return value

    return {
        "status": "accept" if result.returncode == 0 else "reject",
        "returncode": result.returncode,
        "stdout": portable(result.stdout),
        "stderr": portable(result.stderr),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", nargs="?", type=Path, default=PROJECT_ROOT / "testfiles" / "mp4")
    parser.add_argument("--ffmpeg", default="ffmpeg", help="FFmpeg executable (required)")
    parser.add_argument("--ffprobe", default="ffprobe", help="FFprobe executable (required)")
    parser.add_argument("--pymp4-python", default=sys.executable, help="Python interpreter containing pymp4")
    parser.add_argument("--skip-pymp4", action="store_true", help="Compare only genutility and FFmpeg/FFprobe")
    parser.add_argument("--timeout", type=float, default=10, help="Seconds allowed per external parser/file")
    parser.add_argument("--output", type=Path, help="Write complete diagnostics as JSON")
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    directory = args.directory.resolve()
    if not directory.is_dir():
        parser.error("directory does not exist")
    tools = {name: shutil.which(getattr(args, name)) for name in ("ffmpeg", "ffprobe")}
    for name, executable in tools.items():
        if executable is None:
            parser.error(f"{name} is unavailable; install FFmpeg or pass --{name} <executable>")
    if not args.skip_pymp4:
        tools["pymp4"] = shutil.which(args.pymp4_python)
        if tools["pymp4"] is None:
            parser.error("--pymp4-python interpreter is unavailable")
    pymp4_worker = str(PROJECT_ROOT / "tools" / "pymp4_parser.py")
    paths = sorted(path for path in directory.rglob("*") if path.is_file() and path.suffix.lower() in MEDIA_SUFFIXES)
    if not paths:
        parser.error("no media fixtures found")

    manifest = directory / "manifest.json"
    expectations = {}
    parent_manifest = directory.parent / "manifest.json"
    if not manifest.exists() and parent_manifest.exists():
        manifest = parent_manifest
    if manifest.exists():
        fixtures = json.loads(manifest.read_text(encoding="utf-8"))
        if manifest.parent != directory:
            prefix = directory.name + "/"
            fixtures = [
                dict(fixture, file=fixture["file"][len(prefix) :])
                for fixture in fixtures
                if fixture["file"].startswith(prefix)
            ]
        expectations = {fixture["file"]: fixture for fixture in fixtures}
        if len(expectations) != len(fixtures) or set(expectations) != {
            path.relative_to(directory).as_posix() for path in paths
        }:
            parser.error("manifest must describe every media fixture exactly once")

    versions = {
        name: run_parser(
            [executable, "-B", pymp4_worker, "--version"] if name == "pymp4" else [executable, "-version"],
            args.timeout,
            directory,
        )
        for name, executable in tools.items()
    }
    for name, result in versions.items():
        if result["status"] != "accept":
            parser.error(f"cannot run {name}: {result}")
    report = {
        "recorded_at": datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds"),
        "versions": {name: result["stdout"].splitlines()[0] for name, result in versions.items()},
        "files": [],
    }
    failures = 0
    print("file\tgenutility (raw/parsed)\t" + "\t".join(tools))
    for path in paths:
        filename = path.relative_to(directory).as_posix()
        expected = expectations.get(filename)
        entry = {"file": filename, "kind": expected["kind"] if expected else "unclassified", "genutility": []}
        # Run every declared profile/strictness case, as well as both modes on an unclassified input.
        checks = (
            expected["checks"]
            if expected
            else [{"options": [{"parse_atoms": mode, "profile": "auto", "strict": False} for mode in (False, True)]}]
        )
        for check in checks:
            for options in check["options"]:
                actual = parser_result(path, options)
                matches = check.get("expect", actual) == actual
                failures += not matches
                entry["genutility"].append(
                    {
                        "options": options,
                        "status": "reject" if "error" in actual else "accept",
                        "matches": matches,
                        "error": actual.get("error"),
                        **({"actual": actual, "expected": check["expect"]} if not matches else {}),
                    }
                )
        # Force the MOV/MP4 demuxer for box fragments; probing by content alone can choose a different format.
        common = ["-v", "error", "-protocol_whitelist", "file,pipe", "-f", "mov"]
        entry["ffmpeg"] = run_parser(
            [tools["ffmpeg"], "-nostdin", *common, "-i", str(path), "-map", "0", "-c", "copy", "-f", "null", "-"],
            args.timeout,
            directory,
        )
        entry["ffprobe"] = run_parser(
            [tools["ffprobe"], *common, "-show_format", "-show_streams", "-of", "json", str(path)],
            args.timeout,
            directory,
        )
        if "pymp4" in tools:
            entry["pymp4"] = run_parser([tools["pymp4"], "-B", pymp4_worker, str(path)], args.timeout, directory)
        for name in tools:
            result = entry[name]
            required = (expected or {}).get("external", {}).get(name)
            if result["status"] in {"timeout", "unavailable"} or (required and result["status"] != required):
                failures += 1
        modes = [
            next(
                (result["status"] for result in entry["genutility"] if result["options"] == options),
                "-",
            )
            for options in ({"parse_atoms": mode, "profile": "auto", "strict": False} for mode in (False, True))
        ]
        statuses = "\t".join(entry[name]["status"] for name in tools)
        print(f"{filename}\t{'/'.join(modes)}\t{statuses}", flush=True)
        report["files"].append(entry)

    report["failures"] = failures
    report["summary"] = {name: dict(Counter(entry[name]["status"] for entry in report["files"])) for name in tools}
    if args.output:
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(f"{len(paths)} files; {failures} expectation/tool failures; {report['summary']}")
    # A fragment's external rejection is diagnostic, not a validity oracle. Media has explicit expectations.
    return int(bool(failures))


if __name__ == "__main__":
    sys.exit(main())
