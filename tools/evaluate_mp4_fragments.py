"""Assess fragment conversion and build selected complete candidates (Python 3.8+)."""

import argparse
import json
import shutil
import struct
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from genutility.tests.mp4 import parser_result
from tools.compare_mp4_parsers import run_parser

PROJECT_ROOT = Path.cwd()


def boxes(data):
    """Split bounded top-level boxes, preserving their original headers."""
    position = 0
    while position < len(data):
        if len(data) - position < 8:
            raise ValueError("Short box header")
        size, code = struct.unpack_from(">I4s", data, position)
        header_size = 8
        if size == 1:
            if len(data) - position < 16:
                raise ValueError("Short extended box header")
            (size,) = struct.unpack_from(">Q", data, position + 8)
            header_size = 16
        elif size == 0:
            size = len(data) - position
        if not header_size <= size <= len(data) - position:
            raise ValueError("Invalid box size")
        yield code, data[position : position + size], header_size
        position += size


def box(code, body):
    return struct.pack(">I4s", len(body) + 8, code) + body


def build_candidate(base, fragment, recipe):
    """Keep fragment bytes intact; repair only affected enclosing sizes/data offsets."""
    if recipe == "append":
        # Appending after existing media keeps every existing chunk offset valid.
        return base + fragment
    if recipe == "udta":
        if [code for code, _, _ in boxes(fragment)] != [b"udta"]:
            raise ValueError("Asset fragment must contain exactly one udta box")
        return b"".join(
            box(code, data[header:] + fragment) if code == b"moov" else data for code, data, header in boxes(base)
        )
    if recipe == "ftyp":
        if [code for code, _, _ in boxes(fragment)] != [b"ftyp"]:
            raise ValueError("Brand fragment must contain exactly one ftyp")
        old = [data for code, data, _ in boxes(base) if code == b"ftyp"]
        if len(old) != 1:
            raise ValueError("Template must contain exactly one ftyp")
        delta = len(fragment) - len(old[0])

        def rewrite_offsets(data):
            result = []
            for code, encoded, header in boxes(data):
                body = encoded[header:]
                if code == b"ftyp":
                    encoded = fragment
                elif code in (b"moov", b"trak", b"mdia", b"minf", b"stbl"):
                    encoded = box(code, rewrite_offsets(body))
                elif code in (b"stco", b"co64"):
                    width, fmt = (4, ">I") if code == b"stco" else (8, ">Q")
                    (count,) = struct.unpack_from(">I", body, 4)
                    if len(body) != 8 + count * width:
                        raise ValueError("Unexpected chunk-offset table size")
                    encoded = box(
                        code,
                        body[:8]
                        + b"".join(
                            struct.pack(fmt, struct.unpack_from(fmt, body, 8 + index * width)[0] + delta)
                            for index in range(count)
                        ),
                    )
                result.append(encoded)
            return b"".join(result)

        return rewrite_offsets(base)
    if recipe != "tfdt":
        raise ValueError("Unknown conversion recipe")
    if [code for code, _, _ in boxes(fragment)] != [b"tfdt"]:
        raise ValueError("Timing fragment must contain exactly one tfdt box")
    delta = len(fragment) - 20  # The checked-in one-frame template uses a 20-byte version-1 tfdt.
    replacements = 0

    def rewrite(data):
        nonlocal replacements
        output = []
        for code, encoded, header in boxes(data):
            body = encoded[header:]
            if code == b"tfdt":
                if len(encoded) != 20:
                    raise ValueError("Unexpected template tfdt size")
                replacements += 1
                encoded = fragment
            elif code in (b"moof", b"traf"):
                encoded = box(code, rewrite(body))
            elif code == b"trun" and int.from_bytes(body[1:4], "big") & 1:
                (offset,) = struct.unpack_from(">i", body, 8)
                encoded = box(code, body[:8] + struct.pack(">i", offset + delta) + body[12:])
            elif code == b"mfra":
                # The optional index contains the template's old decode time. Omit it instead of retaining it.
                continue
            output.append(encoded)
        return b"".join(output)

    result = rewrite(base)
    if replacements != 1:
        raise ValueError("Template must contain exactly one tfdt")
    return result


def conversion_plan(fixture):
    name = Path(fixture["file"]).name
    if fixture.get("status") in {"rejected", "extraction-rejected"}:
        return (
            "retain-negative",
            "Retain the negative parser/extraction regression; external acceptance would not validate the expected error.",
        )
    if name.startswith("asset-"):
        return "udta", "Insert the unchanged asset udta into the complete H263 movie's moov."
    if name in {"minimal-ftyp-01.mp4", "brands-empty.mp4", "brands-3gp.3gp", "brands-3g2.3g2", "brands-mj2.mj2"}:
        return "ftyp", "Replace the corresponding complete movie's brand box and relocate its chunk offsets."
    if name in {"extended-free.mp4", "uuid-user-type-01.mp4", "uuid-user-type-02.mp4", "size-zero-top-level.mp4"}:
        return "append", "Append the unchanged optional box after complete AVC media; a size-zero box remains last."
    if name in {"tfdt-v0-01.mp4", "tfdt-v1.mp4"}:
        return (
            "tfdt",
            "Replace the fragmented movie's tfdt, repair trun's data offset, and remove the stale optional index.",
        )
    if Path(name).suffix.lower() in {".heic", ".heif", ".avif"}:
        return (
            "needs-image",
            "Requires a real primary image, codec configuration, item properties and rebuilt extents/references.",
        )
    if name.startswith(("sample-", "audio-sample-", "hint-sample-", "part14-mp4s-", "part14-m4ae-", "part14-esds-")):
        return (
            "needs-track",
            "Requires matching encoded samples, valid configuration/descriptors, sample tables and any dependent tracks.",
        )
    if name.startswith(("part14-dpnd-", "part14-ipir-", "part14-mpod-", "part14-sync-", "part14-iods-")):
        return (
            "needs-context",
            "Requires valid referenced tracks or Part 1 descriptors; retaining dangling IDs/placeholder descriptors is not sufficient.",
        )
    if name.startswith(("ctts-", "stts-", "stsc-", "co64-")):
        return (
            "needs-context",
            "Requires matching sample counts and real offsets; these fixtures describe two samples or a synthetic 64-bit position.",
        )
    if name.startswith(("ftyp-", "brands-", "mixed-meta-", "empty-meta-")):
        return (
            "needs-context",
            "Requires a compatible complete file dialect and metadata contents; byte-layout acceptance is not a conformance check.",
        )
    return (
        "needs-context",
        "Requires a case-specific parent, dialect, sample count, valid offsets or referenced tracks; no generic promotion proved.",
    )


def fingerprints(result):
    return [
        [code, size, content, payload["hex"] if payload is not None else None]
        for _, _, code, size, content, payload in result.get("atoms", [])
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=PROJECT_ROOT / "testfiles" / "mp4")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "testtemp" / "mp4-full-candidates")
    parser.add_argument("--report", type=Path, required=True, help="Write the per-fragment assessment as JSON")
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--ffprobe", default="ffprobe")
    parser.add_argument("--timeout", type=float, default=10)
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    corpus = args.corpus.resolve()
    output = args.output_dir.resolve()
    if output == corpus or corpus in output.parents:
        parser.error("candidate output must be outside the checked-in corpus")
    tools = {name: shutil.which(getattr(args, name)) for name in ("ffmpeg", "ffprobe")}
    if not all(tools.values()):
        parser.error("FFmpeg and FFprobe are required")
    output.mkdir(parents=True, exist_ok=True)
    fixtures = json.loads((corpus / "manifest.json").read_text(encoding="utf-8"))
    bases = {
        "udta": (corpus / "ffmpeg" / "media-h263.3gp").read_bytes(),
        "append": (corpus / "ffmpeg" / "media-avc.mp4").read_bytes(),
        "tfdt": (corpus / "ffmpeg" / "media-fragmented-avc.mp4").read_bytes(),
        "ftyp": (corpus / "ffmpeg" / "media-avc.mp4").read_bytes(),
    }
    brand_bases = {
        "brands-3gp.3gp": "ffmpeg/media-h263.3gp",
        "brands-3g2.3g2": "ffmpeg/media-mpeg4.3g2",
        "brands-mj2.mj2": "ffmpeg-derived/media-jpeg2000.mj2",
    }
    versions = {name: run_parser([executable, "-version"], args.timeout, output) for name, executable in tools.items()}
    if any(result["status"] != "accept" for result in versions.values()):
        parser.error("cannot run the external tools")
    report = {
        "recorded_at": datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds"),
        "versions": {name: result["stdout"].splitlines()[0] for name, result in versions.items()},
        "scope": "Complete packet demuxing with original fragment fields/payloads retained; no codec decoding or whole-format conformance claim.",
        "files": [],
    }
    failures = 0
    for fixture in fixtures:
        if fixture["kind"] != "fragment":
            continue
        recipe, reason = conversion_plan(fixture)
        entry = {"file": fixture["file"], "assessment": recipe, "reason": reason}
        if recipe in bases:
            source = corpus / fixture["file"]
            candidate = output / source.name
            base = bases[recipe]
            if source.name in brand_bases:
                base = (corpus / brand_bases[source.name]).read_bytes()
            candidate.write_bytes(build_candidate(base, source.read_bytes(), recipe))
            entry["candidate"] = candidate.name
            entry["preserves_fragment_fields"] = True
            for parsed in (False, True):
                options = {"profile": "auto", "parse_atoms": parsed}
                original = parser_result(source, options)
                actual = parser_result(candidate, options)
                expected = fingerprints(original)
                observed = fingerprints(actual)
                entry["preserves_fragment_fields"] &= (
                    "error" not in original
                    and "error" not in actual
                    and bool(expected)
                    and any(observed[start : start + len(expected)] == expected for start in range(len(observed)))
                )
            common = ["-v", "error", "-protocol_whitelist", "file,pipe", "-f", "mov", "-i", str(candidate)]
            entry["ffmpeg"] = run_parser(
                [tools["ffmpeg"], "-nostdin", *common, "-map", "0", "-c", "copy", "-f", "null", "-"],
                args.timeout,
                output,
            )
            entry["ffprobe"] = run_parser(
                [tools["ffprobe"], *common, "-show_streams", "-show_format", "-show_packets", "-of", "json"],
                args.timeout,
                output,
            )
            if entry["ffprobe"]["status"] == "accept":
                probe = json.loads(entry["ffprobe"]["stdout"])
                entry["media_packets"] = sum(
                    packet.get("codec_type") in {"audio", "video"} for packet in probe.get("packets", [])
                )
                entry["tags"] = probe.get("format", {}).get("tags", {})
            verified = (
                entry["preserves_fragment_fields"]
                and entry["ffmpeg"]["status"] == entry["ffprobe"]["status"] == "accept"
                and entry.get("media_packets", 0) > 0
            )
            entry["assessment"] = "proved-complete" if verified else "conversion-failed"
            failures += not verified
            print(f"{fixture['file']}: {entry['assessment']}", flush=True)
        report["files"].append(entry)
    report["summary"] = dict(Counter(entry["assessment"] for entry in report["files"]))
    report["failures"] = failures
    args.report.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(report["summary"])
    return int(bool(failures))


if __name__ == "__main__":
    sys.exit(main())
