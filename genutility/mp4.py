from __future__ import absolute_import, division, print_function, unicode_literals

import os, re, struct, csv, warnings

import pkg_resources

from .exceptions import ParseError, Break
from .file import read_or_raise

# http://mp4ra.org/#/atoms
# https://wiki.multimedia.cx/index.php/QuickTime_container#QuickTime_Atom_Reference
# https://sno.phy.queensu.ca/~phil/exiftool/TagNames/QuickTime.html

""" `stsd` can be both, be a parent and a leaf atom.
"""

def _load_atoms():
	package_name = __package__ or "genutility"
	atoms_path = pkg_resources.resource_filename(package_name, "data/mp4-atoms.tsv")

	out = {"container": {}, "leaf": {}}

	with open(atoms_path, newline="") as fr:
		for _, type, fourcc, description, _ in csv.reader(fr, delimiter="\t"):
			out[type][fourcc] = description

	return out

atoms = _load_atoms()

atomcodep = re.compile(r"[0-9a-zA-Z]{4}") # what do the specs say here?

def read_atom(fin):

	pos = fin.tell()

	size, code = struct.unpack(">L4s", read_or_raise(fin, 8))

	try:
		code = code.decode("ascii")
		assert bool(atomcodep.match(code))

	except Exception:
		raise ParseError("{!r} @ {} is not a valid atom code".format(code, pos))

	if size == 1: # 64bit size
		size, = struct.unpack(">Q", read_or_raise(fin, 8))

	return pos, code, size

def _enum_atoms(fin, total_size, depth):

	while fin.tell() < total_size:
		pos, type, size = read_atom(fin)

		yield depth, pos, type, size

		if size == 0:
			raise Break("Atom extends to the end of the file") # just stop parsing here

		atom_end = pos + size

		if type in atoms["container"]:
			for atom in _enum_atoms(fin, atom_end, depth+1):
				yield atom

		elif type in atoms["leaf"]:
			fin.seek(atom_end, os.SEEK_SET)

		else: # treat it as leaf and skip it
			warnings.warn("Unknown atom: '{}'. Skipping...".format(type), stacklevel=2)
			fin.seek(atom_end, os.SEEK_SET)

	if fin.tell() != total_size:
		raise ParseError("Invalid file structure. Possibly truncated.")

def enumerate_atoms(path):
	# type: (str, ) -> Iterator[Tuple[int, int, str, int]]

	""" Takes an mp4 file `path` and yields (depth, position, code, size) tuples.
		Unknown atoms will print a warning.
	"""

	total_size = os.path.getsize(path)
	with open(path, "rb") as fr:
		try:
			for atom in _enum_atoms(fr, total_size, 0):
				yield atom
		except Break:
			pass
		except EOFError:
			raise ParseError("Truncated file.")

if __name__ == "__main__":

	import logging
	from pathlib import Path
	from argparse import ArgumentParser
	from genutility.iter import list_except

	parser = ArgumentParser()
	parser.add_argument("drive")
	parser.add_argument("erroronly")
	args = parser.parse_args()

	paths = Path(args.drive).glob("**/*.mp4")

	for path in paths:
		if args.erroronly:
			exc, res = list_except(enumerate_atoms(path))
			if exc:
				print(path)
				for depth, pos, type, size in res:
					print("--"*depth, pos, type, size)
				logging.exception("Enumerating atoms failed", exc_info=exc)
		else:
			print(path)
			for depth, pos, type, size in enumerate_atoms(path):
				print("--"*depth, pos, type, size)
			print()