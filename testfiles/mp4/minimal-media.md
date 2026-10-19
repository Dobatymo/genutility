# Minimal complete media

Generated at `2026-10-05T15:12:43+08:00`, with three raw-audio/mixed-track
regressions added at `2026-10-05T17:13:17+08:00`. Ten codec/box traversal
regressions were added at `2026-10-20T00:51:17+08:00`, also using FFmpeg 8.1.2.
The 40 fixtures cover the brands already represented in the corpus and common native
MOV/ISO-media muxer variants. `minimal-media.json` records sizes, hashes,
major/compatible brands, stream dimensions and packet counts for every file.
File paths are relative to this directory: direct output is in `ffmpeg/`,
and structurally edited output is in `ffmpeg-derived/`.
Codec-specific registered brands beyond these families are not an exhaustive
part of this set.

These are the smallest files among the practical recipes tested, not a proof
of global byte minimality. Every video frame was decoded during fixture
creation and checked for exactly zero RGB pixels. Audio was checked for
silence. Runtime parser tests use the checked-in files and do not require
FFmpeg or codec decoding.

| File relative to this directory | Bytes | Image/sample | Major brand |
| --- | ---: | --- | --- |
| `ffmpeg/minimal-qt.mov` | 636 | 1×1 uncompressed | `qt  ` |
| `ffmpeg/minimal-qt-pcm.mov` | 595 | One silent mono 8-bit PCM sample | `qt  ` |
| `ffmpeg/minimal-qt-video-audio.mov` | 1,079 | 1×1 uncompressed + PCM, video track first | `qt  ` |
| `ffmpeg/minimal-qt-audio-video.mov` | 1,079 | PCM + 1×1 uncompressed, audio track first | `qt  ` |
| `ffmpeg/minimal-isom.mp4` | 708 | 1×1 AV1 | `isom` |
| `ffmpeg/minimal-iso2.mp4` | 756 | 1×1 MPEG-4 Visual | `iso2` |
| `ffmpeg/minimal-iso4.mp4` | 712 | 1×1 AV1 | `iso4` |
| `ffmpeg/minimal-iso5.mp4` | 810 | 1×1 fragmented AV1 | `iso5` |
| `ffmpeg/minimal-iso6.mp4` | 806 | 1×1 fragmented AV1 | `iso6` |
| `ffmpeg/minimal-dash.mp4` | 866 | 1×1 AV1, global segment index | `iso5` + compatible `dash` |
| `ffmpeg/minimal-cmaf.mp4` | 814 | 1×1 fragmented AV1 | `iso6` + compatible `cmfc` |
| `ffmpeg/minimal-mp41.mp4` | 780 | 1×1 MPEG-4 Visual, `iods` | `mp41` |
| `ffmpeg/minimal-mp42.mp4` | 780 | 1×1 MPEG-4 Visual, `iods` | `mp42` |
| `ffmpeg/minimal-avc1.mp4` | 723 | 2×2 AVC | `avc1` |
| `ffmpeg/minimal-3gp4.3gp` | 695 | 1×1 MPEG-4 Visual | `3gp4` |
| `ffmpeg/minimal-3gp6.3gp` | 662 | 2×2 AVC | `3gp6` |
| `ffmpeg/minimal-3gs6.3gp` | 662 | 2×2 AVC | `3gs6` |
| `ffmpeg/minimal-3g2a.3g2` | 695 | 1×1 MPEG-4 Visual | `3g2a` |
| `ffmpeg/minimal-3g2b.3g2` | 662 | 2×2 AVC | `3g2b` |
| `ffmpeg/minimal-m4v.m4v` | 756 | 1×1 MPEG-4 Visual | `M4V ` |
| `ffmpeg/minimal-m4a.m4a` | 722 | Silent mono AAC | `M4A ` |
| `ffmpeg/minimal-isml.mp4` | 875 | 2×2 fragmented AVC | `isml` + compatible `piff` |
| `ffmpeg/minimal-f4v.mp4` | 723 | 2×2 AVC | `f4v ` |
| `ffmpeg/minimal-msnv.mp4` | 1,452 | 1×1 MPEG-4 Visual + AAC | `MSNV` |
| `ffmpeg/minimal-avif.avif` | 303 | 1×1 monochrome AV1 | `avif` + compatible `MA1A` |
| `ffmpeg/minimal-avif-ma1b.avif` | 307 | 1×1 YUV420 AV1 | `avif` + compatible `MA1B` |
| `ffmpeg/minimal-avis.avif` | 1,018 | Two 1×1 AV1 frames | `avis` |
| `ffmpeg-derived/minimal-heic.heic` | 343 | 16×16 HEVC primary image | `heic` |
| `ffmpeg-derived/minimal-mjp2.mj2` | 815 | 1×1 JPEG 2000 | `mjp2` |
| `ffmpeg/minimal-unknown-brand.mp4` | 708 | 1×1 AV1, unknown declaration | `zzzz` |
| `ffmpeg/minimal-hvc1.mp4` | 800 | 16×16 HEVC, out-of-band parameter sets | `isom` |
| `ffmpeg/minimal-hev1.mp4` | 800 | 16×16 HEVC, `hev1` sample entry | `isom` |
| `ffmpeg/minimal-avc3.mp4` | 723 | 2×2 AVC, `avc3` sample entry | `isom` |
| `ffmpeg/minimal-vp9.mp4` | 719 | 1×1 lossless VP9 | `isom` |
| `ffmpeg/minimal-opus.mp4` | 639 | Silent mono 48 kHz Opus input | `isom` |
| `ffmpeg/minimal-flac.mp4` | 686 | Silent mono 48 kHz FLAC | `isom` |
| `ffmpeg/minimal-ac3.mp4` | 1,397 | Silent mono 48 kHz AC-3 input | `isom` |
| `ffmpeg/minimal-eac3.mp4` | 1,399 | Silent mono 48 kHz E-AC-3 input | `isom` |
| `ffmpeg/minimal-cenc.mp4` | 873 | 2×2 AVC, CENC encrypted | `isom` |
| `ffmpeg-derived/minimal-unknown-boxes.mp4` | 784 | 1×1 MPEG-4 Visual with unknown boxes | `mp42` |

AVIF also covers compatible `mif1`, `miaf`, and, for animation, `msf1`/`iso8`.
The animated file stores two frames; FFprobe additionally exposes the first
frame as its primary-image stream. AAC produces two packets when its encoder
is flushed, including priming. PSP requires an audio and a video track, so its
fixture has real samples in both. These are format-specific exceptions to the
single-video-frame recipe.

## Codec and box traversal regressions

The additional sample entries exercise the shared visual/audio prefix and
expose nested `hvcC`, `avcC`, `vpcC`, `dOps`, `dfLa`, `dac3` and `dec3`
configuration boxes. Existing AV1 movies likewise require an `av1C` child.
Configuration payloads remain opaque; header traversal is not codec validation.
All new unencrypted movies decode with FFmpeg. Their video frames are exactly
black. Opus and FLAC decode to exact silence; AC-3/E-AC-3 have the expected lossy
quantization noise (maximum decoded amplitude below 0.000006). Audio encoders
can write a second packet when flushed; metadata records the measured counts.

`minimal-cenc.mp4` contains `encv`, `sinf`, `schm`, `schi` and `tenc` boxes.
It uses the fixed test key `000102030405060708090a0b0c0d0e0f` and key identifier
`101112131415161718191a1b1c1d1e1f`. The bitexact FFmpeg output regenerates
byte-for-byte and is retained as a fixed test vector.
The parser exposes encryption metadata without decrypting samples. To verify
its black video frame with FFmpeg:

```console
ffmpeg -v error -xerror -decryption_key 000102030405060708090a0b0c0d0e0f -i testfiles/mp4/ffmpeg/minimal-cenc.mp4 -f null -
```

`minimal-unknown-boxes.mp4` starts as an FFmpeg MPEG-4 Visual movie. The generator
appends empty boxes with types `a9 78 79 7a` and `00 01 02 03`, followed by a
`free` box containing `NEXT`. This deliberately exercises forward-compatible
reading of bounded unknown box types and continuation, rather than claiming
that the appended extension identifiers are registered. Box sizes and parent
bounds remain validated.

## How size was reduced

The search compared uncompressed RGB/grayscale, MPEG-4 Visual, H263, AVC,
AV1, PNG and JPEG 2000 where supported by each muxer. It then compared AVC
profiles/presets and quantizers, MPEG-4 quantizers, AV1 settings and both
JPEG 2000 encoders. A 1×1 grayscale AVC candidate was slightly larger than
the selected 2×2 baseline candidate. Lossy settings producing near-black
pixels were discarded. MPEG-4 quantizer 21 and AVC CRF 19 preserve exact black
at the minimum observed sizes; AV1 CRF 0 is smaller here than higher CRFs.

Bitexact flags remove variable encoder metadata. Empty handler names, omitted
edit lists and omitted optional bitrate boxes reduce movie overhead. AVC SEI
and HEVC SEI are removed by FFmpeg bitstream filters. Fragmented files retain
their media fragment and necessary offsets; optional trailer indexes are
omitted. Brand flags select the relevant structure rather than changing only
the filename. Brand overrides are used for `iso2`, `mp41`, `mp42`, `avc1`,
`3gs6` and the deliberately unknown `zzzz`; they do not certify conformance to
every brand's rules. See [FFmpeg muxer options](https://ffmpeg.org/ffmpeg-formats.html#MOV_002fMPEG_002d4_002fISOMBFF-muxers).

## HEIF and MJ2 construction

This FFmpeg build has native AVIF output, but no dedicated HEIC or MJ2 muxer.
Their fixtures therefore use FFmpeg-encoded samples followed by explicit
box construction, rather than a renamed or merely rebranded movie:

- HEIC uses one 16×16 HEVC frame from libx265, its actual `hvcC` configuration,
  a primary `hvc1` item, associated `ispe`, and a rebuilt `iloc` extent. The
  selected libx265 encoder does not support a 1×1 frame.
- MJ2 uses OpenJPEG with one resolution level, moves the JP2 header into the
  `mjp2` sample description, retains only the `jp2c` sample, adds the JPEG 2000
  signature and repairs sample sizes, chunk offsets and container lengths.
  Its component precision is eight bits (stored as 7).

Both files demux and decode successfully in FFmpeg. Four complete HEIF/AVIF
fixtures also check that the Exif extractor reports `NoExifFound` when no
Exif item exists.

## Reproduction and regression policy

The byte-for-byte reference environment is:

- Windows, AMD64 (x86-64), OS version `10.0.26200`; Python `3.8.10`.
- Gyan's 64-bit **shared full** build, `8.1.2-full_build-www.gyan.dev`,
  built with GCC `16.1.0` (MSYS2 Rev2).
- [Exact build archive](https://www.gyan.dev/ffmpeg/builds/packages/ffmpeg-8.1.2-full_build-shared.7z),
  published archive SHA-256
  `cba748035c21ce1431d0823c7a3a711f38616f89f87a265dceddf9b7f6749d2d`.
- Local `ffmpeg.exe` SHA-256:
  `9be30133edcc5786f16e632d57e2dab5b259fea9a5243ba99758ca3adc110bd9`.
- The build README identifies FFmpeg source commit `38b88335f9`.

Keep the archive's matching DLLs with `ffmpeg.exe`. The first version line
alone does not distinguish the shared/static package or linked encoder builds.
`minimal-media.json` retains the complete `ffmpeg -version` output (compiler,
configuration and library versions), executable hash and platform details.
Every new `generation.json` records the same provenance fields automatically.
The archive checksum above is the publisher's value; the executable checksum
was measured locally. Byte identity was verified with this environment;
other builds or platforms may produce different bytes.

Run from the repository root:

```console
python -m tools.create_minimal_media --output-dir testtemp/minimal-media
```

Generate replacement fixtures outside the corpus using the encoders and
construction steps described above. `black-1x1.ppm` is the checked-in source
image. Review generated hashes and expectations before promoting changed output; different tool versions can
change bytes. The selected files reproduced byte-for-byte on the recorded
build.

Every new media-parser behavior should use a file-based fixture, preferably
a complete minimal file; use a fragment when isolation or malformed structure
requires it.

`minimal-qt.mov` now passes both raw and parsed traversal: `mdia/hdlr`
selects the visual prefix for a `vide` track and the audio prefix for a `soun`
track. Data handlers in `minf` cannot override it, and context stays within
each media container. Isolated MJ2 PCM entries retain the audio default.
The three added complete fixtures check PCM and both mixed-track orders;
`synthetic/raw-video-short.mov` and `raw-audio-short.mov` check truncated
prefixes with explicit media handlers. PCM generation limits its input to
one 8 kHz sample (`anullsrc=r=8000:cl=mono:nb_samples=1`, input duration
`0.000125`, `pcm_u8`) so a mixed file can still flush its video frame.

Apple documents `raw ` in both [video sample descriptions](https://developer.apple.com/documentation/quicktime-file-format/video_sample_description)
and [sound sample descriptions](https://developer.apple.com/documentation/quicktime-file-format/sound_sample_descriptions).
The [handler reference](https://developer.apple.com/documentation/quicktime-file-format/handler_reference_atom)
identifies the media type; [atom ordering](https://developer.apple.com/documentation/quicktime-file-format/atoms)
requires that handler to precede the media information it handles. This
allows traversal to carry context without rescanning the track.
