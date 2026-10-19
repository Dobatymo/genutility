"""Run pymp4's Box parser to EOF in an isolated process (Python 3.8+)."""

import argparse
import json
import sys
from importlib.metadata import version
from pathlib import Path


def parse_file(path):
    from pymp4.parser import Box

    result = {"boxes": []}
    with path.open("rb") as stream:
        eof = path.stat().st_size
        try:
            while stream.tell() < eof:
                start = stream.tell()
                parsed = Box.parse_stream(stream)
                end = stream.tell()
                if not start < end <= eof:
                    raise ValueError("Box parser did not advance within the file")
                result["boxes"].append(
                    {
                        "offset": start,
                        "end": end,
                        "type": parsed["type"].decode("latin1"),
                        "children": len(parsed.get("children", [])),
                    }
                )
        except Exception as exc:  # noqa: BLE001 - Third-party parser failures are comparison results.
            result["error"] = {"type": type(exc).__name__, "message": str(exc)}
        result["consumed_bytes"] = stream.tell()
        result["file_bytes"] = eof
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", nargs="?", type=Path)
    parser.add_argument("--version", action="store_true")
    args = parser.parse_args()
    try:
        from pymp4.parser import Box  # noqa: F401 - Also check parser import compatibility during startup.
    except ImportError as exc:
        parser.error(f"Cannot import pymp4: {exc}. Install tools/requirements-mp4.txt in this interpreter.")
    if args.version:
        print(f"pymp4 {version('pymp4')}; construct {version('construct')}; Python {sys.version.split()[0]}")
        return 0
    if args.file is None:
        parser.error("a file or --version is required")
    result = parse_file(args.file)
    print(json.dumps(result, ensure_ascii=True))
    return int("error" in result)


if __name__ == "__main__":
    sys.exit(main())
