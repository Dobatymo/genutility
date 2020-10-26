from __future__ import absolute_import, division, print_function, unicode_literals

import hashlib
import zlib
from functools import partial
from os import fspath
from pathlib import Path
from typing import TYPE_CHECKING

from .file import blockfileiter, read_file
from .filesystem import scandir_rec

if TYPE_CHECKING:
	from typing import Callable, Iterable, Iterator, Optional, Union

	from _hashlib import HASH as Hashobj

	from .filesystem import PathType

FILE_IO_BUFFER_SIZE = 8*1024*1024

def hash_file(path, hashcls, chunksize=FILE_IO_BUFFER_SIZE, mode="rb", encoding=None):
	# type: (str, Callable[[], Hashobj], int, str, Optional[str]) -> Hashobj

	m = hashcls()
	for d in blockfileiter(path, mode, encoding, chunk_size=chunksize):
		m.update(d)
	return m

def hash_data(data, hashcls):
	# type: (bytes, Union[Callable[[], Hashobj], str]) -> Hashobj

	""" Hashes `data` with `hashcls`.
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

def crc32_hash_iter(it):
	# type: (Iterable[bytes], ) -> int

	""" Create CRC32 hash from bytes takes from `it`.
	"""

	prev = 0
	for data in it:
		prev = zlib.crc32(data, prev)

	return prev & 0xFFFFFFFF # see https://docs.python.org/3/library/zlib.html#zlib.crc32

def crc32_hash_file(path, chunksize=FILE_IO_BUFFER_SIZE, mode="rb", encoding=None):
	# type: (str, int, str, Optional[str]) -> str

	""" Return crc32 hash of file at `path`. """

	crcint = crc32_hash_iter(blockfileiter(path, mode, encoding, chunk_size=chunksize))
	return format(crcint, "08x")

md5_hash_file = partial(hash_file, hashcls=hashlib.md5)
sha1_hash_file = partial(hash_file, hashcls=hashlib.sha1)

def format_file_hash(hashobj, path):
	# type: (Hashobj, str) -> str

	return "{} *{}".format(hashobj.hexdigest(), path)

def hash_dir_str(path, hashcls=hashlib.sha1, include_names=False):
	# type: (PathType, Callable[[], Hashobj], bool) -> Iterator[str]

	""" sorts names naively, e.g. all uppercase chars come before lowercase """

	m = hashcls()
	for entry in sorted(scandir_rec(path), key=lambda x: x.path):
		filehash = hash_file(entry.path, hashcls)
		yield format_file_hash(filehash, fspath(entry))
		if include_names:
			m.update(entry.name.encode("utf-8"))
		m.update(filehash.digest())
	yield format_file_hash(m, fspath(path))

ed2k_chunksize = 9728000

def ed2k_hash_file_v1(path):
	# type: (Path, ) -> str

	""" Returns ed2k hash.
		This hashing method is used by
		- MLDonkey
		- Shareaza
		- HashCalc

		This differs from `ed2k_hash_file_v2` only if the file size is a multiple of `ed2k_chunksize`.
	"""

	if path.stat().st_size <= ed2k_chunksize:
		return md4_hash_data(read_file(path, "rb")).hexdigest()

	ed2k_hashes = (
		md4_hash_data(data).digest() for data in blockfileiter(path, "rb", chunk_size=ed2k_chunksize)
	)

	return md4_hash_data(b"".join(ed2k_hashes)).hexdigest()

def ed2k_hash_file_v2(path):
	# type: (Path, ) -> str

	""" Returns ed2k hash.
		This hashing method is used by
		- eMule
		- AOM

		This differs from `ed2k_hash_file_v1` only if the file size is a multiple of `ed2k_chunksize`.
	"""

	filesize = path.stat().st_size
	if filesize < ed2k_chunksize:
		return md4_hash_data(read_file(path, "rb")).hexdigest()

	ed2k_hashes = list(
		md4_hash_data(data).digest() for data in blockfileiter(path, "rb", chunk_size=ed2k_chunksize)
	)

	if filesize % ed2k_chunksize == 0:
		ed2k_hashes.append(md4_hash_data(b"").digest())

	return md4_hash_data(b"".join(ed2k_hashes)).hexdigest()
