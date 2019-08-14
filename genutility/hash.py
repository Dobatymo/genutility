from __future__ import absolute_import, division, print_function, unicode_literals

import hashlib, zlib, os.path
from functools import partial
from typing import TYPE_CHECKING

from .file import read_file, blockfileiter
from .filesystem import scandir_rec

if TYPE_CHECKING:
	from typing import Callable, Optional
	from _hashlib import HASH as Hashobj

FILE_IO_BUFFER_SIZE = 8*1024*1024

def hash_file(path, hashcls, chunksize=FILE_IO_BUFFER_SIZE, mode="rb", encoding=None):
	# type: (str, Callable[[], Hashobj], int, str, Optional[str]) -> Hashobj

	m = hashcls()
	for d in blockfileiter(path, mode, encoding, chunk_size=chunksize):
		m.update(d)
	return m

def crc32_hash_iter(it):
	# type: (Iterable[bytes], ) -> int

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
	# type: (str, Callable[[], Hashobj], bool) -> str

	""" sorts names naively, e.g. all uppercase chars come before lowercase """

	m = hashcls()
	for file in sorted(scandir_rec(path), key=lambda x: x.path):
		filehash = hash_file(file, hashcls)
		yield format_file_hash(filehash, file.path)
		if include_names:
			m.update(file.name.encode("utf-8"))
		m.update(filehash.digest())
	yield format_file_hash(m, path)

def md4_hash_data(data):
	# type: (bytes,) -> Hashobj

	hasher = hashlib.new("md4")
	hasher.update(data)
	return hasher

ed2k_chunksize = 9728000

def ed2k_hash_file_v1(path):
	""" Returns ed2k hash.
		This hashing method is used by
		- MLDonkey
		- Shareaza
		- HashCalc
	"""

	if os.path.getsize(path) <= ed2k_chunksize:
		return md4_hash_data(read_file(path, "rb")).hexdigest()

	ed2k_hashes = (
		md4_hash_data(data).digest() for data in blockfileiter(path, "rb", chunk_size=ed2k_chunksize)
	)

	return md4_hash_data(b"".join(ed2k_hashes)).hexdigest()

def ed2k_hash_file_v2(path):
	""" Returns ed2k hash.
		This hashing method is used by
		- eMule
		- AOM
	"""

	filesize = os.path.getsize(path)
	if filesize < ed2k_chunksize:
		return md4_hash_data(read_file(path, "rb")).hexdigest()

	ed2k_hashes = list(
		md4_hash_data(data).digest() for data in blockfileiter(path, "rb", chunk_size=ed2k_chunksize)
	)

	if filesize % ed2k_chunksize == 0:
		ed2k_hashes.append(md4_hash_data(b"").digest())

	return md4_hash_data(b"".join(ed2k_hashes)).hexdigest()
