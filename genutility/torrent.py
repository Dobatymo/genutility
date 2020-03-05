from __future__ import absolute_import, division, print_function, unicode_literals

import json
from hashlib import sha1

from bencode import bdecode, bencode # bencoding ?

from .file import read_file, blockfileiter, blockfilesiter
from .filesystem import FileProperties
from .json import BuiltinEncoder

def read_torrent_info_dict(path):
	return bdecode(read_file(path, "rb"))["info"]

def iter_torrent(path):
	""" Returns file informations from a torrent file. 
		Hash (SHA-1) is obtained according to BEP0047 (if available).
	"""

	info = read_torrent_info_dict(path)

	try:
		files = info["files"]
	except KeyError:
		yield FileProperties(info["name"], info["length"], False, hash=info.get("sha1"))
	else:
		for fd in files:
			path = "/".join(fd["path"])
			yield FileProperties(info["name"] + "/" + path, fd["length"], False, hash=fd.get("sha1"))

def torrent_to_json(path, indent="\t"):
	torrent = bdecode(read_file(path, "rb"))
	return json.dumps(torrent, ensure_ascii=False, indent=indent, cls=BuiltinEncoder)

def pieces_field(pieces):
	return b"".join(sha1(piece).digest() for piece in pieces)  # nosec

def create_torrent_info_dict(path, piece_size, private=None):
	# type: (Path, int, Optional[int]) -> dict

	assert private is None or private in {0, 1}

	if path.is_file():
		ret = {
			"name": path.name,
			"length": path.stat().st_size,
			"piece length": piece_size,
			"pieces": pieces_field(blockfileiter(path, chunk_size=piece_size)),
		}

	elif path.is_dir():
		files = []

		assert files

		ret = {
			"name": path.name,
			"files": [{
				"length": length,
				"path": path.parts,
			} for length, path in files],
			"piece length": piece_size,
			"pieces": pieces_field(blockfilesiter((p for l, p in files), chunk_size=piece_size)),
		}

	else:
		raise ValueError("path neither file nor directory")

	if private is not None:
		ret["private"] = private

	return ret

def torrent_info_hash(d):
	return sha1(bencode(d)).hexdigest()  # nosec

def get_torrent_hash(path):
	return torrent_info_hash(read_torrent_info_dict(path))

def create_torrent(path, piece_size, announce=""):
	# type: (Path, int, str) -> bytes

	info = create_torrent_info_dict(path, piece_size)
	torrent = {
		"info": info,
		"announce": announce
	}

	return bencode(torrent)

if __name__ == "__main__":
	from argparse import ArgumentParser
	from genutility.args import existing_path

	parser = ArgumentParser()
	parser.add_argument("torrentfile", type=existing_path)
	args = parser.parse_args()

	print(torrent_to_json(args.torrentfile))
