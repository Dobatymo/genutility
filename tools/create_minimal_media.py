"""Recreate the minimal complete media fixtures outside the corpus (Python 3.8+)."""

import argparse
import hashlib
import json
import platform
import shutil
import struct
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tools.evaluate_mp4_fragments import box, boxes

PROJECT_ROOT = Path.cwd()

CODECS = {
    "raw": ["-c:v", "rawvideo", "-pix_fmt", "gray"],
    "mpeg4": ["-c:v", "mpeg4", "-pix_fmt", "yuv420p", "-q:v", "21"],
    "avc": [
        "-vf",
        "scale=2:2",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-preset",
        "ultrafast",
        "-profile:v",
        "baseline",
        "-crf",
        "19",
        "-bsf:v",
        "filter_units=remove_types=6",
    ],
    "av1": ["-c:v", "libaom-av1", "-pix_fmt", "gray", "-cpu-used", "8", "-crf", "0", "-still-picture", "1"],
    "vp9": ["-c:v", "libvpx-vp9", "-pix_fmt", "yuv420p", "-lossless", "1"],
    "jpeg2000": ["-c:v", "libopenjpeg", "-pix_fmt", "gray", "-numresolution", "1", "-tag:v", "mjp2"],
    "hevc": [
        "-vf",
        "scale=16:16",
        "-c:v",
        "libx265",
        "-pix_fmt",
        "yuv420p",
        "-preset",
        "veryslow",
        "-crf",
        "51",
        "-x265-params",
        "log-level=error:info=0:pools=none:frame-threads=1",
        "-bsf:v",
        "filter_units=remove_types=39|40",
        "-tag:v",
        "hvc1",
    ],
}

CODECS["av1-color"] = [*CODECS["av1"][:3], "yuv420p", *CODECS["av1"][4:]]

AUDIO_CODECS = {
    "audio": "aac",
    "raw-pcm": "pcm_u8",
    "raw-av": "pcm_u8",
    "opus": "libopus",
    "flac": "flac",
    "ac3": "ac3",
    "eac3": "eac3",
}

# Major-brand variants are real muxer outputs, not file-extension aliases.
SPECS = [
    ("minimal-qt.mov", "mov", "raw", []),
    ("minimal-qt-pcm.mov", "mov", "raw-pcm", []),
    ("minimal-qt-video-audio.mov", "mov", "raw-av", ["-map", "0:v", "-map", "1:a"]),
    ("minimal-qt-audio-video.mov", "mov", "raw-av", ["-map", "1:a", "-map", "0:v"]),
    ("minimal-isom.mp4", "mp4", "av1", []),
    ("minimal-iso2.mp4", "mp4", "mpeg4", ["-brand", "iso2"]),
    ("minimal-iso4.mp4", "mp4", "av1", ["-movflags", "+negative_cts_offsets"]),
    ("minimal-iso5.mp4", "mp4", "av1", ["-movflags", "+frag_keyframe+empty_moov+default_base_moof+skip_trailer"]),
    (
        "minimal-iso6.mp4",
        "mp4",
        "av1",
        ["-movflags", "+frag_keyframe+empty_moov+default_base_moof+negative_cts_offsets+skip_trailer"],
    ),
    (
        "minimal-dash.mp4",
        "mp4",
        "av1",
        ["-movflags", "+dash+global_sidx+frag_keyframe+empty_moov+default_base_moof+skip_trailer"],
    ),
    ("minimal-cmaf.mp4", "mp4", "av1", ["-movflags", "+cmaf+skip_trailer"]),
    ("minimal-mp41.mp4", "mp4", "mpeg4", ["-brand", "mp41", "-skip_iods", "0", "-iods_video_profile", "1"]),
    ("minimal-mp42.mp4", "mp4", "mpeg4", ["-brand", "mp42", "-skip_iods", "0", "-iods_video_profile", "1"]),
    ("minimal-avc1.mp4", "mp4", "avc", ["-brand", "avc1"]),
    ("minimal-3gp4.3gp", "3gp", "mpeg4", []),
    ("minimal-3gp6.3gp", "3gp", "avc", []),
    ("minimal-3gs6.3gp", "3gp", "avc", ["-brand", "3gs6"]),
    ("minimal-3g2a.3g2", "3g2", "mpeg4", []),
    ("minimal-3g2b.3g2", "3g2", "avc", []),
    ("minimal-m4v.m4v", "ipod", "mpeg4", []),
    ("minimal-m4a.m4a", "ipod", "audio", []),
    ("minimal-isml.mp4", "ismv", "avc", ["-movflags", "+skip_trailer"]),
    ("minimal-f4v.mp4", "f4v", "avc", []),
    ("minimal-msnv.mp4", "psp", "mpeg4", []),
    ("minimal-avif.avif", "avif", "av1", []),
    ("minimal-avif-ma1b.avif", "avif", "av1-color", []),
    ("minimal-avis.avif", "avif", "animated-av1", []),
    ("minimal-heic.heic", "mp4", "hevc", []),
    ("minimal-mjp2.mj2", "mov", "jpeg2000", []),
    ("minimal-unknown-brand.mp4", "mp4", "av1", ["-brand", "zzzz"]),
    ("minimal-hvc1.mp4", "mp4", "hevc", []),
    ("minimal-hev1.mp4", "mp4", "hevc", ["-tag:v", "hev1"]),
    ("minimal-avc3.mp4", "mp4", "avc", ["-tag:v", "avc3"]),
    ("minimal-vp9.mp4", "mp4", "vp9", []),
    ("minimal-opus.mp4", "mp4", "opus", []),
    ("minimal-flac.mp4", "mp4", "flac", ["-strict", "-2"]),
    ("minimal-ac3.mp4", "mp4", "ac3", []),
    ("minimal-eac3.mp4", "mp4", "eac3", []),
    (
        "minimal-cenc.mp4",
        "mp4",
        "avc",
        [
            "-encryption_scheme",
            "cenc-aes-ctr",
            "-encryption_key",
            "000102030405060708090a0b0c0d0e0f",
            "-encryption_kid",
            "101112131415161718191a1b1c1d1e1f",
        ],
    ),
    ("minimal-unknown-boxes.mp4", "mp4", "mpeg4", ["-brand", "mp42"]),
]


def movie_children(code, body):
    if code in {b"moov", b"trak", b"mdia", b"minf", b"dinf", b"stbl"}:
        return body
    if code == b"stsd":
        return body[8:]
    if code in {b"hvc1", b"mjp2"}:
        return body[78:]
    return None


def find_body(data, wanted):
    for code, encoded, header in boxes(data):
        body = encoded[header:]
        if code == wanted:
            return body
        children = movie_children(code, body)
        if children is not None:
            found = find_body(children, wanted)
            if found is not None:
                return found
    return None


def make_heif(movie):
    """Wrap one length-prefixed HEVC sample using its actual hvcC and dimensions."""
    config = find_body(movie, b"hvcC")
    sample = find_body(movie, b"mdat")
    entry = find_body(movie, b"hvc1")
    if config is None or sample is None or entry is None:
        raise ValueError("Expected a one-sample hvc1 movie")
    width, height = struct.unpack_from(">HH", entry, 24)
    ftyp = box(b"ftyp", b"heic" + b"\0" * 4 + b"heicmif1")
    hdlr = box(b"hdlr", b"\0" * 8 + b"pict" + b"\0" * 13)
    pitm = box(b"pitm", b"\0" * 4 + struct.pack(">H", 1))
    infe = box(b"infe", b"\x02\0\0\0" + struct.pack(">HH", 1, 0) + b"hvc1\0")
    iinf = box(b"iinf", b"\0" * 4 + struct.pack(">H", 1) + infe)
    ipco = box(b"ipco", box(b"hvcC", config) + box(b"ispe", b"\0" * 4 + struct.pack(">II", width, height)))
    ipma = box(b"ipma", b"\0" * 4 + struct.pack(">IHB", 1, 1, 2) + b"\x81\x02")

    def metadata(offset):
        iloc = box(b"iloc", b"\0" * 4 + b"\x44\0" + struct.pack(">HHHHII", 1, 1, 0, 1, offset, len(sample)))
        return box(b"meta", b"\0" * 4 + hdlr + pitm + iloc + iinf + box(b"iprp", ipco + ipma))

    return ftyp + metadata(len(ftyp) + len(metadata(0)) + 8) + box(b"mdat", sample)


def make_mj2(movie):
    """Move the JP2 header into the MJ2 sample entry and retain a jp2c sample."""
    image = find_body(movie, b"mdat")
    if image is None:
        raise ValueError("Missing JPEG 2000 sample")
    jp2h = bytearray(find_body(image, b"jp2h"))
    codestream = find_body(image, b"jp2c")
    if jp2h[4:8] != b"ihdr" or codestream is None:
        raise ValueError("Expected the native encoder's JP2 structure")
    if jp2h[18] != 7:
        raise ValueError("Expected eight-bit unsigned JPEG 2000 components")
    sample = box(b"jp2c", codestream)
    prefix = box(b"jP  ", b"\r\n\x87\n") + box(b"ftyp", b"mjp2" + b"\0" * 4 + b"mjp2")

    def rewrite(code, body):
        children = movie_children(code, body)
        if children is not None:
            skip = len(body) - len(children)
            body = body[:skip] + b"".join(rewrite(c, data[h:]) for c, data, h in boxes(children))
        if code == b"mjp2":
            body = body[:78] + box(b"jp2h", bytes(jp2h)) + body[78:]
        elif code == b"stco":
            if body[:8] != b"\0" * 4 + struct.pack(">I", 1):
                raise ValueError("Expected one sample chunk")
            body = body[:8] + struct.pack(">I", len(prefix) + 8)
        elif code == b"stsz":
            body = body[:4] + struct.pack(">II", len(sample), 1)
        return box(code, body)

    return prefix + box(b"mdat", sample) + rewrite(b"moov", find_body(movie, b"moov"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--corpus", type=Path, default=PROJECT_ROOT / "testfiles" / "mp4")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "testtemp" / "minimal-media")
    args = parser.parse_args()
    output = args.output_dir.resolve()
    corpus = args.corpus.resolve()
    if output == corpus or corpus in output.parents:
        parser.error("Generate outside the checked-in corpus; review changes before promotion")
    ffmpeg = shutil.which(args.ffmpeg)
    if ffmpeg is None:
        parser.error("FFmpeg is unavailable")
    output.mkdir(parents=True, exist_ok=True)
    source = corpus / "black-1x1.ppm"
    records = []
    for filename, muxer, codec, extra in SPECS:
        group = (
            "ffmpeg-derived"
            if filename in {"minimal-heic.heic", "minimal-mjp2.mj2", "minimal-unknown-boxes.mp4"}
            else "ffmpeg"
        )
        relative = Path(group) / filename
        target = output / relative
        target.parent.mkdir(exist_ok=True)
        command = [ffmpeg, "-v", "error", "-y"]
        if codec == "animated-av1":
            command += ["-loop", "1"]
        has_video = codec not in AUDIO_CODECS or codec == "raw-av"
        if has_video:
            command += ["-i", str(source)]
        if codec in AUDIO_CODECS or muxer == "psp":
            pcm = codec in {"raw-pcm", "raw-av"}
            rate = 8000 if codec in {"audio", "raw-pcm", "raw-av"} or muxer == "psp" else 48000
            source_audio = f"anullsrc=r={rate}:cl=mono" + (":nb_samples=1" if pcm else "")
            command += ["-f", "lavfi"]
            if pcm:
                command += ["-t", "0.000125"]  # One 8 kHz sample; allow the video input to reach EOF too.
            command += ["-i", source_audio, "-c:a", AUDIO_CODECS.get(codec, "aac")]
            if not pcm:
                command += ["-frames:a", "1"]
        else:
            command += ["-an"]
        if has_video:
            opts = CODECS["av1"][:-2] if codec == "animated-av1" else CODECS["raw" if codec == "raw-av" else codec]
            # The PPM itself has one frame. Let mixed inputs reach EOF so both
            # streams flush real packets before output closes.
            if muxer != "psp" and codec != "raw-av":
                command += ["-frames:v", "2" if codec == "animated-av1" else "1"]
            command += opts
        command += [
            "-threads",
            "1",
            "-map_metadata",
            "-1",
            "-fflags",
            "+bitexact",
            "-flags:v",
            "+bitexact",
            "-flags:a",
            "+bitexact",
        ]
        if muxer != "avif":
            command += ["-use_editlist", "0", "-write_btrt", "0", "-empty_hdlr_name", "1"]
        command += [*extra, "-f", muxer, str(target)]
        subprocess.run(command, check=True, timeout=30)  # noqa: S603
        if filename == "minimal-heic.heic":
            target.write_bytes(make_heif(target.read_bytes()))
        elif codec == "jpeg2000":
            target.write_bytes(make_mj2(target.read_bytes()))
        elif filename == "minimal-unknown-boxes.mp4":
            target.write_bytes(
                target.read_bytes() + box(b"\xa9xyz", b"") + box(b"\0\1\2\3", b"") + box(b"free", b"NEXT")
            )
        records.append(
            {
                "file": relative.as_posix(),
                "muxer": muxer,
                "codec": codec,
                "options": extra,
                "bytes": target.stat().st_size,
                "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            }
        )
        print(f"{filename}: {target.stat().st_size} bytes", flush=True)
    version_output = subprocess.check_output([ffmpeg, "-version"], text=True).splitlines()  # noqa: S603
    report = {
        "recorded_at": datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds"),
        "ffmpeg": version_output[0],
        "ffmpeg_version_output": version_output,
        "ffmpeg_binary_sha256": hashlib.sha256(Path(ffmpeg).read_bytes()).hexdigest(),
        "platform": {"system": platform.system(), "version": platform.version(), "machine": platform.machine()},
        "python": platform.python_version(),
        "files": records,
    }
    (output / "generation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
