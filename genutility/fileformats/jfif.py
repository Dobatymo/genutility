import logging
import mmap
import re
from struct import unpack
from typing import IO, Iterator, Optional, Set, Tuple, Union

from _hashlib import HASH as Hashobj

from ..exceptions import ParseError
from ..file import BufferedBinaryIoT, read_or_raise
from ..string import backslash_escaped_ascii

Segment = Union[Tuple[str, bytes], Tuple[str, bytes, bytes, bytes]]

segments = {
    # ISO/IEC 10918-1 : 1993(E), Table B.1
    # Start Of Frame markers, non-differential, Huffman coding
    b"\xff\xc0": ("SOF0", True, "Start of frame 0, baseline DCT"),
    b"\xff\xc1": ("SOF1", True, "Start of Frame 1, Extended Sequential DCT"),
    b"\xff\xc2": ("SOF2", True, "Start of frame 2, progressive DCT"),
    b"\xff\xc3": ("SOF3", True, "Start of Frame 3, Lossless (Sequential)"),
    # Start Of Frame markers, differential, Huffman coding
    b"\xff\xc5": ("SOF5", True, "Differential sequential DCT"),
    b"\xff\xc6": ("SOF6", True, "Differential progressive DCT"),
    b"\xff\xc7": ("SOF7", True, "Differential lossless (sequential)"),
    # Start Of Frame markers, non-differential, arithmetic coding"),
    b"\xff\xc8": ("JPG", True, "Reserved for JPEG extensions"),
    b"\xff\xc9": ("SOF9", True, "Extended sequential DCT"),
    b"\xff\xca": ("SOF10", True, "Progressive DCT"),
    b"\xff\xcb": ("SOF11", True, "Lossless (sequential)"),
    # Start Of Frame markers, differential, arithmetic coding
    b"\xff\xcd": ("SOF13", True, "Differential sequential DCT"),
    b"\xff\xce": ("SOF14", True, "Differential progressive DCT"),
    b"\xff\xcf": ("SOF15", True, "Differential lossless (sequential)"),
    # Huffman table specification
    b"\xff\xc4": ("DHT", True, "Define Huffman table(s)"),
    # Arithmetic coding conditioning specification
    b"\xff\xcc": ("DAC", True, "Define arithmetic coding conditioning(s)"),
    # Restart interval termination
    b"\xff\xd0": ("RST0", False, "Restart with modulo 8 count `m`"),
    b"\xff\xd1": ("RST1", False, "Restart with modulo 8 count `m`"),
    b"\xff\xd2": ("RST2", False, "Restart with modulo 8 count `m`"),
    b"\xff\xd3": ("RST3", False, "Restart with modulo 8 count `m`"),
    b"\xff\xd4": ("RST4", False, "Restart with modulo 8 count `m`"),
    b"\xff\xd5": ("RST5", False, "Restart with modulo 8 count `m`"),
    b"\xff\xd6": ("RST6", False, "Restart with modulo 8 count `m`"),
    b"\xff\xd7": ("RST7", False, "Restart with modulo 8 count `m`"),
    # Other markers
    b"\xff\xd8": ("SOI", False, "Start of image"),
    b"\xff\xd9": ("EOI", False, "End of image"),
    b"\xff\xda": ("SOS", True, "Start of scan"),
    b"\xff\xdb": ("DQT", True, "Define quantization table(s)"),
    b"\xff\xdc": ("DNL", True, "Define number of lines"),
    b"\xff\xdd": ("DRI", True, "Define restart interval"),
    b"\xff\xde": ("DHP", True, "Define hierarchical progression"),
    b"\xff\xdf": ("EXP", True, "Expand reference component(s)"),
    b"\xff\xe0": ("APP0", True, "Reserved for application segments"),
    b"\xff\xe1": ("APP1", True, "Reserved for application segments"),
    b"\xff\xe2": ("APP2", True, "Reserved for application segments"),
    b"\xff\xe3": ("APP3", True, "Reserved for application segments"),
    b"\xff\xe4": ("APP4", True, "Reserved for application segments"),
    b"\xff\xe5": ("APP5", True, "Reserved for application segments"),
    b"\xff\xe6": ("APP6", True, "Reserved for application segments"),
    b"\xff\xe7": ("APP7", True, "Reserved for application segments"),
    b"\xff\xe8": ("APP8", True, "Reserved for application segments"),
    b"\xff\xe9": ("APP9", True, "Reserved for application segments"),
    b"\xff\xea": ("APP10", True, "Reserved for application segments"),
    b"\xff\xeb": ("APP11", True, "Reserved for application segments"),
    b"\xff\xec": ("APP12", True, "Reserved for application segments"),
    b"\xff\xed": ("APP13", True, "Reserved for application segments"),
    b"\xff\xee": ("APP14", True, "Reserved for application segments"),
    b"\xff\xef": ("APP15", True, "Reserved for application segments"),
    b"\xff\xf0": ("JPG0", True, "Reserved for JPEG extensions"),
    b"\xff\xf1": ("JPG1", True, "Reserved for JPEG extensions"),
    b"\xff\xf2": ("JPG2", True, "Reserved for JPEG extensions"),
    b"\xff\xf3": ("JPG3", True, "Reserved for JPEG extensions"),
    b"\xff\xf4": ("JPG4", True, "Reserved for JPEG extensions"),
    b"\xff\xf5": ("JPG5", True, "Reserved for JPEG extensions"),
    b"\xff\xf6": ("JPG6", True, "Reserved for JPEG extensions"),
    b"\xff\xf7": ("JPG7", True, "Reserved for JPEG extensions"),
    b"\xff\xf8": ("JPG8", True, "Reserved for JPEG extensions"),
    b"\xff\xf9": ("JPG9", True, "Reserved for JPEG extensions"),
    b"\xff\xfa": ("JPG10", True, "Reserved for JPEG extensions"),
    b"\xff\xfb": ("JPG11", True, "Reserved for JPEG extensions"),
    b"\xff\xfc": ("JPG12", True, "Reserved for JPEG extensions"),
    b"\xff\xfd": ("JPG13", True, "Reserved for JPEG extensions"),
    b"\xff\xfe": ("COM", True, "Comment"),
    # Reserved markers
    b"\xff\x01": ("TEM", False, "For temporary private use in arithmetic coding"),
    # b"\xFF\x02" to b"\xFF\xBF": ("RES", True, "Reserved"),
}

markerp = re.compile(b"\xff[^\x00]")  # don't use raw literals

metadata_segments = {
    "COM",
    "TRAILER",
} | {f"APP{i}" for i in range(16)}


def iter_jpeg_fp(fr: IO[bytes], translate: bool = True) -> Iterator[Segment]:
    """Iterate over JPEG file given in binary stream `fr` and yield the segments.
    `translate=False` can be used to reconstruct the file in a bit-identical way.
    See copy_jpeg() for an example.
    """

    with mmap.mmap(fr.fileno(), 0, access=mmap.ACCESS_READ) as mm:
        fs = mm.size()

        eoi = False

        while True:
            if not eoi:
                marker = read_or_raise(mm, 2)
            else:
                data = mm.read()
                if data:
                    if translate:
                        yield "TRAILER", data
                    else:
                        yield "TRAILER", b"", b"", data
                return

            try:
                info = segments[marker]
            except KeyError:
                raise ParseError(f"Invalid segment marker: {backslash_escaped_ascii(marker)} at {mm.tell()}")

            name = info[0]
            hasdata = info[1]

            if name == "SOS":
                size = read_or_raise(mm, 2)
                (length,) = unpack(">H", size)
                data = read_or_raise(mm, length - 2)

                if translate:
                    yield name, data
                else:
                    yield name, marker, size, data

                prevenv = mm.tell()
                for m in markerp.finditer(mm, prevenv, fs):
                    start, end = m.span(0)
                    if translate:
                        yield "ENTROPY", mm[prevenv:start]
                    else:
                        yield "ENTROPY", b"", b"", mm[prevenv:start]
                    prevenv = end

                    marker = m.group(0)

                    try:
                        info = segments[marker]
                    except KeyError:
                        raise ParseError(f"Invalid segment marker: {backslash_escaped_ascii(marker)} at {start}")

                    name = info[0]

                    if name[:3] == "RST":
                        if translate:
                            yield name, b""
                        else:
                            yield name, marker, b"", b""
                    else:
                        mm.seek(start)  # this is seeking back
                        break

            else:
                eoi = eoi or name == "EOI"

                if hasdata:
                    size = read_or_raise(mm, 2)
                    (length,) = unpack(">H", size)
                    data = read_or_raise(mm, length - 2)
                else:
                    size = b""
                    data = b""

                if translate:
                    yield name, data
                else:
                    yield name, marker, size, data


def iter_jpeg(path: str, translate: bool = True) -> Iterator[Segment]:
    """Same as `iter_jpeg_fp()` except that it accepts a path."""

    with open(path, "rb") as fr:
        yield from iter_jpeg_fp(fr, translate=translate)


def copy_jpeg_fp(fin: IO[bytes], fout: BufferedBinaryIoT, ignore_segments: Optional[Set[str]] = None) -> None:
    """Same as `copy_jpeg()` except that it accepts file-like objects."""

    ignore_segments = ignore_segments or set()

    for name, marker, size, data in iter_jpeg_fp(fin, translate=False):
        if name not in ignore_segments:
            fout.write(marker)
            fout.write(size)
            fout.write(data)


def copy_jpeg(inpath: str, outpath: str, ignore_segments: Optional[Set[str]] = None) -> None:
    """Copy JPEG file `inpath` to `outpath` while ignoring the JPEG segments
    given in `ignore_segments`.

    Example:
            copy_jpeg("in.jpg", "out.jpg", {"COM", "TRAILER"})
    """

    with open(inpath, "rb") as fr, open(outpath, "xb") as fw:
        copy_jpeg_fp(fr, fw, ignore_segments=ignore_segments)


def hash_raw_jpeg(path: str, hashobj: Hashobj) -> None:
    """Create a hash of the JPEG at `path` skipping over meta data sections."""

    for name, marker, size, data in iter_jpeg(path, translate=False):
        if name not in metadata_segments:
            hashobj.update(marker)
            hashobj.update(size)
            hashobj.update(data)


if __name__ == "__main__":
    from argparse import ArgumentParser
    from hashlib import sha1

    from genutility.args import is_dir
    from genutility.hash import hashsum_file_format
    from genutility.iter import consume

    parser = ArgumentParser()
    parser.add_argument("path", type=is_dir)
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-r", "--recursive", action="store_true")
    parser.add_argument("--hash", action="store_true")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    if args.recursive:
        it = args.path.rglob("*.jpg")
    else:
        it = args.path.glob("*.jpg")

    valid = 0
    invalid = 0

    for path in it:
        try:
            if args.hash:
                hashobj = sha1()  # nosec
                hash_raw_jpeg(path, hashobj)
                print(hashsum_file_format(hashobj, path))
            else:
                consume(iter_jpeg(path))

        except ParseError as e:
            logging.debug("Parse error in %s: %s", path, e)
            invalid += 1

        except EOFError:
            logging.debug("Truncated file %s", path)
            invalid += 1

        else:
            valid += 1

    print("valid", valid, "invalid", invalid)
