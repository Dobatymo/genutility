from __future__ import generator_stop

import logging
import mmap
import re
from struct import unpack
from typing import TYPE_CHECKING, BinaryIO, Iterator, Optional, Set, Tuple, Union

from ..exceptions import ParseError
from ..file import read_or_raise
from ..string import backslash_escaped_ascii

if TYPE_CHECKING:

    from _hashlib import HASH as Hashobj

    Segment = Union[Tuple[str, bytes], Tuple[str, bytes, bytes, bytes]]

segments = {
    # ISO/IEC 10918-1 : 1993(E), Table B.1
    # Start Of Frame markers, non-differential, Huffman coding
    b"\xFF\xC0": ("SOF0", True, "Start of frame 0, baseline DCT"),
    b"\xFF\xC1": ("SOF1", True, "Start of Frame 1, Extended Sequential DCT"),
    b"\xFF\xC2": ("SOF2", True, "Start of frame 2, progressive DCT"),
    b"\xFF\xC3": ("SOF3", True, "Start of Frame 3, Lossless (Sequential)"),
    # Start Of Frame markers, differential, Huffman coding
    b"\xFF\xC5": ("SOF5", True, "Differential sequential DCT"),
    b"\xFF\xC6": ("SOF6", True, "Differential progressive DCT"),
    b"\xFF\xC7": ("SOF7", True, "Differential lossless (sequential)"),
    # Start Of Frame markers, non-differential, arithmetic coding"),
    b"\xFF\xC8": ("JPG", True, "Reserved for JPEG extensions"),
    b"\xFF\xC9": ("SOF9", True, "Extended sequential DCT"),
    b"\xFF\xCA": ("SOF10", True, "Progressive DCT"),
    b"\xFF\xCB": ("SOF11", True, "Lossless (sequential)"),
    # Start Of Frame markers, differential, arithmetic coding
    b"\xFF\xCD": ("SOF13", True, "Differential sequential DCT"),
    b"\xFF\xCE": ("SOF14", True, "Differential progressive DCT"),
    b"\xFF\xCF": ("SOF15", True, "Differential lossless (sequential)"),
    # Huffman table specification
    b"\xFF\xC4": ("DHT", True, "Define Huffman table(s)"),
    # Arithmetic coding conditioning specification
    b"\xFF\xCC": ("DAC", True, "Define arithmetic coding conditioning(s)"),
    # Restart interval termination
    b"\xFF\xD0": ("RST0", False, "Restart with modulo 8 count `m`"),
    b"\xFF\xD1": ("RST1", False, "Restart with modulo 8 count `m`"),
    b"\xFF\xD2": ("RST2", False, "Restart with modulo 8 count `m`"),
    b"\xFF\xD3": ("RST3", False, "Restart with modulo 8 count `m`"),
    b"\xFF\xD4": ("RST4", False, "Restart with modulo 8 count `m`"),
    b"\xFF\xD5": ("RST5", False, "Restart with modulo 8 count `m`"),
    b"\xFF\xD6": ("RST6", False, "Restart with modulo 8 count `m`"),
    b"\xFF\xD7": ("RST7", False, "Restart with modulo 8 count `m`"),
    # Other markers
    b"\xFF\xD8": ("SOI", False, "Start of image"),
    b"\xFF\xD9": ("EOI", False, "End of image"),
    b"\xFF\xDA": ("SOS", True, "Start of scan"),
    b"\xFF\xDB": ("DQT", True, "Define quantization table(s)"),
    b"\xFF\xDC": ("DNL", True, "Define number of lines"),
    b"\xFF\xDD": ("DRI", True, "Define restart interval"),
    b"\xFF\xDE": ("DHP", True, "Define hierarchical progression"),
    b"\xFF\xDF": ("EXP", True, "Expand reference component(s)"),
    b"\xFF\xE0": ("APP0", True, "Reserved for application segments"),
    b"\xFF\xE1": ("APP1", True, "Reserved for application segments"),
    b"\xFF\xE2": ("APP2", True, "Reserved for application segments"),
    b"\xFF\xE3": ("APP3", True, "Reserved for application segments"),
    b"\xFF\xE4": ("APP4", True, "Reserved for application segments"),
    b"\xFF\xE5": ("APP5", True, "Reserved for application segments"),
    b"\xFF\xE6": ("APP6", True, "Reserved for application segments"),
    b"\xFF\xE7": ("APP7", True, "Reserved for application segments"),
    b"\xFF\xE8": ("APP8", True, "Reserved for application segments"),
    b"\xFF\xE9": ("APP9", True, "Reserved for application segments"),
    b"\xFF\xEA": ("APP10", True, "Reserved for application segments"),
    b"\xFF\xEB": ("APP11", True, "Reserved for application segments"),
    b"\xFF\xEC": ("APP12", True, "Reserved for application segments"),
    b"\xFF\xED": ("APP13", True, "Reserved for application segments"),
    b"\xFF\xEE": ("APP14", True, "Reserved for application segments"),
    b"\xFF\xEF": ("APP15", True, "Reserved for application segments"),
    b"\xFF\xF0": ("JPG0", True, "Reserved for JPEG extensions"),
    b"\xFF\xF1": ("JPG1", True, "Reserved for JPEG extensions"),
    b"\xFF\xF2": ("JPG2", True, "Reserved for JPEG extensions"),
    b"\xFF\xF3": ("JPG3", True, "Reserved for JPEG extensions"),
    b"\xFF\xF4": ("JPG4", True, "Reserved for JPEG extensions"),
    b"\xFF\xF5": ("JPG5", True, "Reserved for JPEG extensions"),
    b"\xFF\xF6": ("JPG6", True, "Reserved for JPEG extensions"),
    b"\xFF\xF7": ("JPG7", True, "Reserved for JPEG extensions"),
    b"\xFF\xF8": ("JPG8", True, "Reserved for JPEG extensions"),
    b"\xFF\xF9": ("JPG9", True, "Reserved for JPEG extensions"),
    b"\xFF\xFA": ("JPG10", True, "Reserved for JPEG extensions"),
    b"\xFF\xFB": ("JPG11", True, "Reserved for JPEG extensions"),
    b"\xFF\xFC": ("JPG12", True, "Reserved for JPEG extensions"),
    b"\xFF\xFD": ("JPG13", True, "Reserved for JPEG extensions"),
    b"\xFF\xFE": ("COM", True, "Comment"),
    # Reserved markers
    b"\xFF\x01": ("TEM", False, "For temporary private use in arithmetic coding"),
    # b"\xFF\x02" to b"\xFF\xBF": ("RES", True, "Reserved"),
}

markerp = re.compile(b"\xFF[^\x00]")  # don't use raw literals

metadata_segments = {
    "COM",
    "TRAILER",
} | {f"APP{i}" for i in range(16)}


def iter_jpeg_fp(fr, translate=True):
    # type: (BinaryIO, bool) -> Iterator[Segment]

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
                for m in markerp.finditer(mm, prevenv, fs):  # type: ignore
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


def iter_jpeg(path, translate=True):
    # type: (str, bool) -> Iterator[Segment]

    """Same as `iter_jpeg_fp()` except that it accepts a path."""

    with open(path, "rb") as fr:
        yield from iter_jpeg_fp(fr, translate=translate)


def copy_jpeg_fp(fin, fout, ignore_segments=None):
    # type: (BinaryIO, BinaryIO, Optional[Set[str]]) -> None

    """Same as `copy_jpeg()` except that it accepts file-like objects."""

    ignore_segments = ignore_segments or set()

    for name, marker, size, data in iter_jpeg_fp(fin, translate=False):
        if name not in ignore_segments:
            fout.write(marker)
            fout.write(size)
            fout.write(data)


def copy_jpeg(inpath, outpath, ignore_segments=None):
    # type: (str, str, Set[str]) -> None

    """Copy JPEG file `inpath` to `outpath` while ignoring the JPEG segments
    given in `ignore_segments`.

    Example:
            copy_jpeg("in.jpg", "out.jpg", {"COM", "TRAILER"})
    """

    with open(inpath, "rb") as fr, open(outpath, "xb") as fw:
        copy_jpeg_fp(fr, fw, ignore_segments=ignore_segments)


def hash_raw_jpeg(path, hashobj):
    # type: (str, Hashobj) -> None

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
