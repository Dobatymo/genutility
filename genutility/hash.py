import hashlib
import zlib
from functools import partial
from pathlib import Path
from typing import IO, Callable, Optional, Union

from _hashlib import HASH as Hashobj

from .file import PathType, blockfileiter, iterfilelike, read_file

HashCls = Union[Callable[[], Hashobj], str]

FILE_IO_BUFFER_SIZE = 8 * 1024 * 1024


class HashobjCRC:  # don't inherit from Hashobj (TypeError: cannot create 'HashobjCRC' instances)
    digest_size = 4
    name = "crc"

    def __init__(self) -> None:
        self.prev = 0

    def update(self, data: bytes) -> None:
        """Update the hash object with the bytes-like object.
        Repeated calls are equivalent to a single call with the concatenation of all the arguments:
        m.update(a); m.update(b) is equivalent to m.update(a+b).
        """

        self.prev = zlib.crc32(data, self.prev)

    def digest(self) -> bytes:
        """Return the digest of the data passed to the update() method so far.
        This is a bytes object of size digest_size which may contain bytes in the whole range from 0 to 255.
        """

        return (self.prev & 0xFFFFFFFF).to_bytes(4, "big", signed=False)

    def hexdigest(self) -> str:
        """Like digest() except the digest is returned as a string object of double length,
        containing only hexadecimal digits. This may be used to exchange the value safely in email or other non-binary environments.
        """

        return self.digest().hex()

    def copy(self) -> "HashobjCRC":
        """Return a copy (“clone”) of the hash object.
        This can be used to efficiently compute the digests of data sharing a common initial substring.
        """

        out = HashobjCRC()
        out.prev = self.prev
        return out


def hash_file(
    path: PathType,
    hashcls: HashCls,
    chunk_size: int = FILE_IO_BUFFER_SIZE,
    mode: str = "rb",
    buffering: int = -1,
    encoding: Optional[str] = None,
    opener=None,
) -> Hashobj:
    # fixme: does this even work with `mode="rt"`?

    if isinstance(hashcls, str):
        m = hashlib.new(hashcls)
    else:
        m = hashcls()
    for d in blockfileiter(path, mode, buffering, encoding, chunk_size=chunk_size, opener=opener):
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
crc_hash_data = partial(hash_data, hashcls=HashobjCRC)

md5_hash_file = partial(hash_file, hashcls=hashlib.md5)
sha1_hash_file = partial(hash_file, hashcls=hashlib.sha1)
crc32_hash_file = partial(hash_file, hashcls=HashobjCRC)  # output changed in v0.0.104


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
