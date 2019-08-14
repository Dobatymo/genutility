from __future__ import absolute_import, division, print_function, unicode_literals

from bencode import bdecode

from .file import read_file
from .filesystem import FileProperties

def iter_torrent(path):
	""" Returns file informations from a torrent file. 
		Hash (SHA-1) is obtained according to BEP0047 (if available).
	"""

	info = bdecode(read_file(path, "rb"))["info"]

	try:
		files = info["files"]
	except KeyError:
		yield FileProperties(info['name'], info['length'], False, hash=info.get("sha1"))
	else:
		for fd in files:
			path = "/".join(fd['path'])
			yield FileProperties(info['name'] + "/" + path, fd['length'], False, hash=fd.get("sha1"))

if __name__ == "__main__":
	from argparse import ArgumentParser

	parser = ArgumentParser()
	parser.add_argument("torrentfile")
	args = parser.parse_args()

	print(list(iter_torrent(args.torrentfile)))
