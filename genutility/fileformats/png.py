from __future__ import generator_stop

import logging
import re
import zlib
from struct import pack, unpack
from typing import TYPE_CHECKING

from ..exceptions import ParseError
from ..file import read_or_raise

if TYPE_CHECKING:
    from typing import IO, Callable, Iterator, Optional, Tuple

    from _hashlib import HASH as Hashobj

png_sig = b"\x89PNG\r\n\x1a\n"
chunk_type_p = re.compile(rb"^[a-zA-Z]{4}$")

image_chunks = {b"IHDR", b"IDAT", b"PLTE", b"tRNS", b"acTL", b"fcTL", b"fdAT", b"IEND"}
image_meta_chunks = {b"sBIT", b"pHYs", b"vpAg", b"gAMA", b"sRGB", b"cHRM", b"iCCP"}
meta_data_chunks = {b"iTXt", b"tEXt", b"zTXt", b"tIME", b"bKGD", b"eXIf", b"dSIG"}


def png_chunk(chunk_type_ascii, chunk):
    # type: (str, bytes) -> bytes

    chunk_type = chunk_type_ascii.encode("ascii")

    length = pack("!I", len(chunk))
    _crc = zlib.crc32(chunk_type)
    _crc = zlib.crc32(chunk, _crc)
    crc = pack("!i", _crc)
    return length + chunk_type + chunk + crc


def IHDR(width, height):
    # type: (int, int) -> bytes

    bitdepth = 1
    colortype = 0  # grayscale
    compression = 0
    filter = 0
    interlace = 0
    chunk = pack("!IIBBBBB", width, height, bitdepth, colortype, compression, filter, interlace)

    return png_chunk("IHDR", chunk)


def IEND():
    # type: () -> bytes

    return png_chunk("IEND", b"")


def IDAT(binary, level=9):
    # type: (bytes, int) -> bytes

    # ignores filter for scanlines
    return png_chunk("IDAT", zlib.compress(binary, level))


def binary2png(binary, width, height):
    # type: (bytes, int, int) -> bytes

    return png_sig + IHDR(width, height) + IDAT(binary) + IEND()


def iter_png_fp(stream, translate=True, verify_crc=True):
    # type: (IO[bytes], bool, bool) -> Iterator[tuple]

    """Parses PNG / APNG files."""

    signature = read_or_raise(stream, 8)
    if signature != png_sig:
        raise ParseError("Not a png file")

    if not translate:
        yield (b"", b"", signature, b"")

    iend = False

    while True:
        data = stream.read(8)

        if not data:
            if iend:
                return
            else:
                raise EOFError
        elif len(data) != 8:
            raise EOFError

        length, chunk_type = unpack(">I4s", data)
        if not chunk_type_p.match(chunk_type):
            raise ParseError(f"Invalid chunk type: {chunk_type} at {stream.tell() - 4}")

        chunk_type_ascii = chunk_type.decode("ascii")

        if chunk_type_ascii == "IEND":
            iend = True

        if length > 0:
            chunk = read_or_raise(stream, length)
        else:
            chunk = b""

        data_crc = read_or_raise(stream, 4)
        (crc,) = unpack(">I", data_crc)

        if verify_crc:
            _crc = zlib.crc32(chunk_type)
            _crc = zlib.crc32(chunk, _crc)
            if crc != _crc:
                raise ParseError("Invalid CRC")

        if translate:
            yield chunk_type_ascii, chunk, crc
        else:
            yield data[0:4], data[4:8], chunk, data_crc


def iter_png(path, translate=True, verify_crc=True):
    # type: (str, bool, bool) -> Iterator[tuple]

    """Same as `iter_png_fp()` except that it accepts a path."""

    with open(path, "rb") as fr:
        yield from iter_png_fp(fr, translate=translate, verify_crc=verify_crc)


def copy_png_fp(fin, fout, filter_chunks=None, verify_crc=False):
    # type: (IO[bytes], IO[bytes], Optional[Callable[[bytes], bool]], bool) -> None

    """Same as `copy_png()` except that it accepts file-like objects."""

    filter_chunks = filter_chunks or (lambda chunk_type: True)

    for length, chunk_type, chunk, crc in iter_png_fp(fin, translate=False, verify_crc=verify_crc):
        if filter_chunks(chunk_type):
            fout.write(length)
            fout.write(chunk_type)
            fout.write(chunk)
            fout.write(crc)


def copy_png(inpath, outpath, filter_chunks=None, verify_crc=False):
    # type: (str, str, Callable[[bytes], bool], bool) -> None

    """Copy PNG file `inpath` to `outpath` while ignoring the PNG chunks
    given by `filter_chunks`.

    Example:
            copy_jpeg("in.png", "out.png", lambda chunk: chunk not in {"tEXt", "tIME"})
    """

    with open(inpath, "rb") as fr, open(outpath, "xb") as fw:
        copy_png_fp(fr, fw, filter_chunks=filter_chunks, verify_crc=verify_crc)


def hash_raw_png(path, hashobj):
    # type: (str, Hashobj) -> None

    """Create a hash of the JPEG at `path` skipping over meta data sections."""

    def filter_chunks(ct):
        # type: (bytes, ) -> bool

        return ct in image_chunks

    for length, chunk_type, chunk, crc in iter_png(path, translate=False, verify_crc=False):
        if filter_chunks(chunk_type):
            hashobj.update(length)
            hashobj.update(chunk_type)
            hashobj.update(chunk)


def parse_tEXt(chunk):
    # type: (bytes, ) -> Tuple[str, str]

    keyword, text = chunk.split(b"\0")
    return keyword.decode("latin1"), text.decode("latin1")


def parse_tIME(chunk):
    # type: (bytes, ) -> Tuple[int, int, int, int, int, int]

    year, month, day, hour, minute, second = unpack("!HBBBBB", chunk)

    return year, month, day, hour, minute, second


if __name__ == "__main__":
    from argparse import ArgumentParser

    from genutility.args import is_dir
    from genutility.iter import consume

    parser = ArgumentParser()
    parser.add_argument("path", type=is_dir)
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-r", "--recursive", action="store_true")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    if args.recursive:
        it = args.path.rglob("*.png")
    else:
        it = args.path.glob("*.png")

    valid = 0
    invalid = 0

    for path in it:
        try:
            consume(iter_png(path))

        except ParseError as e:
            logging.debug("ParseError in %s: %s", path, e)
            invalid += 1

        except EOFError:
            logging.debug("EOFError in %s", path)
            invalid += 1

        else:
            valid += 1

    print("valid", valid, "invalid", invalid)
