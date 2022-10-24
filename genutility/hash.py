from __future__ import generator_stop

import hashlib
import zlib
from functools import partial
from pathlib import Path
from typing import IO, Callable, Iterable, Optional, Union

from _hashlib import HASH as Hashobj

from .file import blockfileiter, iterfilelike, read_file

HashCls = Union[Callable[[], Hashobj], str]

FILE_IO_BUFFER_SIZE = 8 * 1024 * 1024


def hash_file(
    path: str, hashcls: HashCls, chunk_size: int = FILE_IO_BUFFER_SIZE, mode: str = "rb", encoding: Optional[str] = None
) -> Hashobj:

    # fixme: does this even work with `mode="rt"`?

    if isinstance(hashcls, str):
        m = hashlib.new(hashcls)
    else:
        m = hashcls()
    for d in blockfileiter(path, mode, encoding, chunk_size=chunk_size):
        m.update(d)
    return m


def hash_filelike(fr: IO[bytes], hashcls: HashCls, chunk_size: int = FILE_IO_BUFFER_SIZE) -> Hashobj:
    if isinstance(hashcls, str):
        m = hashlib.new(hashcls)
    else:
        m = hashcls()

    for d in iterfilelike(fr, chunk_size=chunk_size):
        m.update(d)
    return m


def hash_data(data: bytes, hashcls: HashCls) -> Hashobj:

    """Hashes `data` with `hashcls`.
    `hashcls` can either be a string like "md5" or a hash object like `hashlib.md5`.
    """

    if isinstance(hashcls, str):
        m = hashlib.new(hashcls)
    else:
        m = hashcls()
    m.update(data)
    return m


md4_hash_data = partial(hash_data, hashcls="md4")
md5_hash_data = partial(hash_data, hashcls=hashlib.md5)
sha1_hash_data = partial(hash_data, hashcls=hashlib.sha1)


def crc32_hash_iter(it: Iterable[bytes]) -> int:

    """Create CRC32 hash from bytes takes from `it`."""

    prev = 0
    for data in it:
        prev = zlib.crc32(data, prev)

    return prev & 0xFFFFFFFF  # see https://docs.python.org/3/library/zlib.html#zlib.crc32


def crc32_hash_file(
    path: str, chunk_size: int = FILE_IO_BUFFER_SIZE, mode: str = "rb", encoding: Optional[str] = None
) -> str:

    """Return crc32 hash of file at `path`."""

    crcint = crc32_hash_iter(blockfileiter(path, mode, encoding, chunk_size=chunk_size))
    return format(crcint, "08x")


md5_hash_file = partial(hash_file, hashcls=hashlib.md5)
sha1_hash_file = partial(hash_file, hashcls=hashlib.sha1)


def hashsum_file_format(hashobj: Hashobj, path: str) -> str:

    return f"{hashobj.hexdigest()} *{path}"


ed2k_chunksize = 9728000


def ed2k_hash_file_v1(path: Path) -> str:

    """Returns ed2k hash.
    This hashing method is used by
    - MLDonkey
    - Shareaza
    - HashCalc

    This differs from `ed2k_hash_file_v2` only if the file size is a multiple of `ed2k_chunksize`.
    """

    if path.stat().st_size <= ed2k_chunksize:
        return md4_hash_data(read_file(path, "rb")).hexdigest()

    ed2k_hashes = (md4_hash_data(data).digest() for data in blockfileiter(path, "rb", chunk_size=ed2k_chunksize))

    return md4_hash_data(b"".join(ed2k_hashes)).hexdigest()


def ed2k_hash_file_v2(path: Path) -> str:

    """Returns ed2k hash.
    This hashing method is used by
    - eMule
    - AOM

    This differs from `ed2k_hash_file_v1` only if the file size is a multiple of `ed2k_chunksize`.
    """

    filesize = path.stat().st_size
    if filesize < ed2k_chunksize:
        return md4_hash_data(read_file(path, "rb")).hexdigest()

    ed2k_hashes = list(md4_hash_data(data).digest() for data in blockfileiter(path, "rb", chunk_size=ed2k_chunksize))

    if filesize % ed2k_chunksize == 0:
        ed2k_hashes.append(md4_hash_data(b"").digest())

    return md4_hash_data(b"".join(ed2k_hashes)).hexdigest()
