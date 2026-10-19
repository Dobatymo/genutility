# Development tools

Run these tools from the repository root. The comparison accepts an optional
input directory; the assessment and fixture generator accept `--corpus` to
select a different input corpus.

`compare_mp4_parsers.py` scans every MP4/QuickTime/HEIF/3GP/3G2/MJ2 fixture recursively.
It runs every genutility profile/mode/strictness check declared in a corpus
manifest, or both auto-profile modes when no manifest exists. It then runs
FFmpeg, FFprobe and [pymp4](https://github.com/beardypig/pymp4) on every input.
The FFmpeg commands force their MOV demuxer so a small box fragment cannot be
mistaken for another format.

```console
python -m tools.compare_mp4_parsers --output testtemp/mp4-parser-results.json
python -m tools.compare_mp4_parsers testfiles/mp4/ffmpeg
python -m tools.compare_mp4_parsers testfiles/mp4/ffmpeg-derived
python -m tools.compare_mp4_parsers testfiles/mp4/synthetic
python -m tools.compare_mp4_parsers testfiles/mp4/regression
python -m tools.compare_mp4_parsers path/to/fixtures --timeout 20
python -m tools.compare_mp4_parsers --ffmpeg path/to/ffmpeg --ffprobe path/to/ffprobe
python -m tools.compare_mp4_parsers --pymp4-python path/to/venv/python
python -m tools.compare_mp4_parsers --skip-pymp4
```

Requires Python 3.8+, the project's ordinary dependencies, and FFmpeg with
both command-line executables. Install `tools/requirements-mp4.txt` into the
pymp4 interpreter. By default this is the interpreter running the comparison;
`--pymp4-python` selects a separate environment, recommended because pymp4
pins the older Construct 2.8.8. These dependencies are only for this development
tool and are not genutility runtime requirements. For example, on Windows:

```console
python -m venv testtemp/pymp4-env
testtemp/pymp4-env/Scripts/python -m pip install -r tools/requirements-mp4.txt
python -m tools.compare_mp4_parsers --pymp4-python testtemp/pymp4-env/Scripts/python.exe --output testtemp/mp4-parser-results.json
testtemp/pymp4-env/Scripts/python -m unittest tools.test_pymp4_parser
```

On Unix, use `testtemp/pymp4-env/bin/python`. `--skip-pymp4` preserves the
comparison without this optional dependency. The script reuses the fixture
test's result serializer; HEIF Exif
extraction and CLI behavior are checked by the unit suite separately.
When scanning a source subdirectory, it filters the parent manifest to that
group and retains all internal and external expectations.

- FFmpeg demuxes all packets with stream copy into its null output. This tests
  container/packet reading, without decoding compressed frames.
- FFprobe reports format and stream metadata as JSON. This tests header
  probing; it can succeed on files FFmpeg cannot process through the end.
- pymp4 runs `Box.parse_stream` repeatedly to EOF, following its `mp4dump`
  CLI's approach. Each file runs in a fresh subprocess under the same timeout.
  Its JSON diagnostics retain the successfully parsed top-level prefix,
  immediate child counts, consumed bytes and exception type/message. The
  adapter checks forward progress but does not replace or repair pymp4's
  parser. Using its `MP4`/`GreedyRange` API instead could hide a failed suffix.
- FFmpeg/FFprobe permit local file/pipe protocols only; pymp4 reads the local
  input directly. None opens a GUI.
- Rejections, timeouts and diagnostics are retained per file, and the scan
  continues. The default external-command timeout is 10 seconds.
- Missing executables, an empty input directory or incomplete manifest stop
  with a clear error. A timeout, tool launch failure, internal expectation
  mismatch or explicit external expectation mismatch produces a nonzero exit.
  Missing or incompatible pymp4 stops during the startup import/version check.
- A fragment's external rejection is diagnostic. Only fixtures with explicit
  `external` expectations require external acceptance/rejection. Without a
  manifest, statuses are diagnostic and do not imply conformance.

The optional JSON report records versions, a Taiwan-local ISO timestamp,
internal case results, tool return codes and full external diagnostics.
Input-root paths are replaced with `<INPUT_ROOT>` for portability.

pymp4 acceptance means its box reader reached EOF without an exception.
Unknown boxes may remain opaque, and failed nested children can be hidden by
its internal `GreedyRange` parsers. This is neither semantic field parity with
genutility nor FFmpeg's media-packet validation. Ordinary pymp4 rejections
are diagnostic unless the manifest explicitly sets a pymp4 expectation.

Comparison reports are generated outputs, not checked-in resources. The
`--output` command above records exact tool versions, per-file diagnostics,
expectation mismatches and totals for the selected corpus. Some malformed
fragments are accepted by FFprobe or pymp4, so acceptance counts cannot rank
correctness. The corpus contains 322 inputs and 2,058 internal parser cases.
Those cases include declaration-first dialect selection:
`ftyp` selects ISO/QuickTime, and structural detection applies only without it.
They also cover Part 14 systems/enhancement sample entries, MPEG-4 track
references, malformed layouts, future descriptor-box versions and handler-based
selection of raw video/audio sample-entry prefixes.

The shared runtime is `genutility.fileformats.isobmff`:

```console
python -m genutility.fileformats.isobmff testfiles/mp4 --recursive --errors-only
python -m genutility.fileformats.isobmff testfiles/mp4/ffmpeg-derived/media-jpeg2000.mj2
```

The test corpus includes deliberate invalid inputs, so its first command
reports expected parser failures. `testfiles/mp4/README.md` documents the
shared atom table, supported extensions, specification sources and limits.

Command reference: [FFmpeg documentation](https://ffmpeg.org/ffmpeg.html)
and [FFprobe documentation](https://ffmpeg.org/ffprobe.html).

## Recreate minimal complete fixtures

```console
python -m tools.create_minimal_media --output-dir testtemp/minimal-media
```

This creates the 40 selected minimal files using FFmpeg and the checked-in
1×1 black PPM source. Output mirrors the corpus's `ffmpeg/` and
`ffmpeg-derived/` directories; report file paths are relative to the output
directory. HEIC and MJ2 additionally require explicit item/sample
box construction from their encoded movie samples. It leaves the corpus and
manifest unchanged, and supports `--ffmpeg` and `--corpus` for a different
input corpus. See
`testfiles/mp4/minimal-media.md` for sizes, supported brands, codec choices and
the exact Windows/FFmpeg build and reproduction instructions. `generation.json`
records the full FFmpeg version/configuration output, executable SHA-256,
platform and Python version. Three fixtures cover PCM
audio and both mixed-track orders. Regeneration preserves the original 27
files byte-for-byte with the recorded build. Additional complete movies cover
HEVC, AVC3, VP9, Opus, FLAC, AC-3, E-AC-3 and CENC scheme metadata. The unknown
box fixture appends two bounded unknown boxes and a final `free` box to an
FFmpeg-generated movie. CENC uses the fixed test key documented in
`testfiles/mp4/minimal-media.md`; the runtime parser does not decrypt it.

## Evaluate fragment conversion

```console
python -m tools.evaluate_mp4_fragments --report testtemp/mp4-fragment-assessment.json
```

This script inventories every manifest fragment and implements four finite
conversion recipes using the existing complete movies. It writes candidates
to `testtemp/mp4-full-candidates/`; `--output-dir` may select another directory
outside the corpus. It leaves the original fixtures and expectations intact.
Use `--ffmpeg`, `--ffprobe` and `--timeout` as with the comparison script.

Each demonstrated conversion retains the original decoded fields and raw
payloads in both traversal modes, passes FFmpeg packet demuxing and FFprobe,
and yields an audio/video packet. The portable JSON report includes per-file
reasons, diagnostics, tool versions, tags and a Taiwan-local timestamp. A
candidate or tool failure returns a nonzero exit code.

The `--report` command writes the assessment as a generated JSON output. The
275 committed fragments include 28 demonstrated conversions, 30 cases needing
complete image construction, 27 needing matching tracks, 92 needing specific
context and 98 retained negative expectations. The other classifications
describe work still needed, not impossibility.
Successful demuxing does not validate optional metadata that FFmpeg ignores,
codec decoding or complete standards conformance. Details and exact candidate
names are recorded in the generated assessment report.
