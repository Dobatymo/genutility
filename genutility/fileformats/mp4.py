from __future__ import generator_stop

import logging
import os
import re
import struct
import warnings
from base64 import b64decode
from collections import namedtuple
from typing import IO, Dict, Iterable, Iterator, List, Optional, Tuple

import pkg_resources

from ..csv import iter_csv
from ..exceptions import Break, ParseError
from ..file import read_or_raise
from ..iter import batch

# http://mp4ra.org/#/atoms
# https://wiki.multimedia.cx/index.php/QuickTime_container#QuickTime_Atom_Reference
# https://sno.phy.queensu.ca/~phil/exiftool/TagNames/QuickTime.html

""" mp4notes
	`stsd` can be both, be a parent and a leaf atom.
	`meta` can be both, be a parent and a leaf atom.
"""

class BoxParser:

	def __init__(self, fin, size=None):
		self.fin = fin
		self.size = size
		self.delta = 0

	def unpack(self, format, size):
		ret = struct.unpack(format, read_or_raise(self.fin, size))
		self.delta += size
		return ret

	@staticmethod
	def read_c_string(fin, size):
		ret = []
		while len(ret) < size:
			c = fin.read(1)
			ret.append(c)
			if c == b"\0":
				break
		return b"".join(ret)

	def c_string(self, encoding=None):
		s = self.read_c_string(self.fin, self.size - self.delta)
		self.delta += len(s)
		s = s.rstrip(b"\0")
		if encoding is None:
			return s
		else:
			try:
				return s.decode(encoding)
			except UnicodeDecodeError:
				ret = s.decode("latin-1") # should never fail
				logging.warning("'%s' is not a valid %s string", ret, encoding)
				return ret

def named_batch(entries: Iterable, length: int, named_tuple_cls: object) -> List[namedtuple]:
	return list(batch(entries, length, named_tuple_cls._make))

# names tuples

SampleToChunkEntry = namedtuple("SampleToChunkEntry", ["first_chunk", "samples_per_chunk", "sample_description_index"])
CompositionOffsetEntry = namedtuple("CompositionOffsetEntry", ["sample_count", "sample_offset"])
TimeToSampleEntry = namedtuple("TimeToSampleEntry", ["sample_count", "sample_delta"])
FilePartitionEntry = namedtuple("FilePartitionEntry", ["block_count", "block_size"])

# atoms

def stco(fin, size, version, flags):
	""" ChunkOffsetBox """

	assert version == 0
	p = BoxParser(fin, size)

	entry_count, = p.unpack(">L", 4)
	chunk_offsets = p.unpack(f">{entry_count}L", entry_count*4)

	return {"chunk_offsets": chunk_offsets}, p.delta

def fpar(fin, size, version, flags):
	""" FilePartitionBox """

	assert version in (0, 1)
	p = BoxParser(fin, size)

	if version == 0:
		item_ID, = p.unpack(">H", 2)
	elif version == 1:
		item_ID, = p.unpack(">L", 4)

	packet_payload_size, reserved, FEC_encoding_ID, FEC_instance_ID, max_source_block_length, encoding_symbol_length, max_number_of_encoding_symbols = p.unpack(">H2B4H", 12)
	assert reserved == 0

	scheme_specific_info = b64decode(p.c_string("ascii"))
	if version == 0:
		entry_count, = p.unpack(">H", 2)
	elif version == 1:
		entry_count, = p.unpack(">L", 4)

	entries = p.unpack(f">{'HL'*entry_count}", entry_count*6)
	return {
		"item_ID": item_ID,
		"packet_payload_size": packet_payload_size,
		"FEC_encoding_ID": FEC_encoding_ID,
		"FEC_instance_ID": FEC_instance_ID,
		"max_source_block_length": max_source_block_length,
		"encoding_symbol_length": encoding_symbol_length,
		"max_number_of_encoding_symbols": max_number_of_encoding_symbols,
		"scheme_specific_info": scheme_specific_info,
		"file_partition_entries": named_batch(entries, 2, FilePartitionEntry)
	}, p.delta

def mfhd(fin, size, version, flags):
	""" MovieFragmentHeaderBox """

	assert version == 0
	p = BoxParser(fin, size)

	sequence_number, = p.unpack(">L", 4)

	return {"sequence_number": sequence_number}, p.delta

def co64(fin, size, version, flags):
	assert version == 0
	p = BoxParser(fin, size)

	entry_count, = p.unpack(">L", 4)
	chunk_offsets = p.unpack(f">{entry_count}Q", entry_count*8)

	return {"chunk_offsets": chunk_offsets}, p.delta

def prft(fin, size, version, flags):

	p = BoxParser(fin, size)

	if version == 0:
		reference_track_ID, ntp_timestamp, media_time= p.unpack(">LQL", 16)
	elif version == 1:
		reference_track_ID, ntp_timestamp, media_time= p.unpack(">LQQ", 20)
	else:
		assert False

	return {"reference_track_ID": reference_track_ID, "ntp_timestamp": ntp_timestamp, "media_time": media_time}, p.delta

def dimg(fin, size, version, flags):

	""" Not a fullbox, inherits parent version """

	p = BoxParser(fin, size)

	if version == 0:
		from_item_id, = p.unpack(">H", 2)
	elif version == 1:
		from_item_id, = p.unpack(">L", 4)
	else:
		assert False

	to_item_ids_num, = p.unpack(">H", 2)

	if version == 0:
		to_item_ids = p.unpack(f">{to_item_ids_num}H", to_item_ids_num*2)
	elif version == 1:
		to_item_ids = p.unpack(f">{to_item_ids_num}L", to_item_ids_num*4)
	else:
		assert False

	return {"from_item_id": from_item_id, "to_item_ids": to_item_ids}, p.delta

def ctts(fin, size, version, flags):
	""" Composition Time to Sample Box / CompositionOffsetBox """
	p = BoxParser(fin, size)

	entry_count, = p.unpack(">L", 4)

	if version == 0:
		entries = p.unpack(f">{entry_count*2}L", entry_count*2*4)
	elif version == 1:
		entries = p.unpack(f">{'Ll'*entry_count}", entry_count*2*4)
	else:
		assert False

	return {"composition_offset_entries": named_batch(entries, 2, CompositionOffsetEntry)}, p.delta

def stsc(fin, size, version, flags):
	""" Sample To Chunk Box """

	assert version == 0
	p = BoxParser(fin, size)
	entry_count, = p.unpack(">L", 4)
	entries = p.unpack(f">{entry_count*3}L", entry_count*3*4)
	return {"sample_to_chunk_entries": named_batch(entries, 3, SampleToChunkEntry)}, p.delta

def stts(fin, size, version, flags):
	""" TimeToSampleBox """

	assert version == 0
	p = BoxParser(fin, size)
	entry_count, = p.unpack(">L", 4)
	entries = p.unpack(f">{entry_count*2}L", entry_count*2*4)
	return {"time_to_samples_entries": named_batch(entries, 2, TimeToSampleEntry)}, p.delta

def uuid(fin, size, version, flags):
	p = BoxParser(fin, size)
	uuid, = p.unpack(">16s", 16)
	return {"uuid": uuid}, p.delta

def ftyp(fin, size, version, flags):
	p = BoxParser(fin, size)
	major_brand, minor_version = p.unpack(">4sL", 8)
	return {"major_brand": major_brand, "minor_version": minor_version}, p.delta

def stsd(fin, size, version, flags):
	assert version == 0
	p = BoxParser(fin, size)
	entry_count, = p.unpack(">L", 4)
	return {"entry_count": entry_count}, p.delta

def url(fin, size, version, flags):
	assert version == 0
	p = BoxParser(fin, size)
	url = p.c_string("utf-8")
	return {"url": url}, p.delta

def urn(fin, size, version, flags):
	assert version == 0
	p = BoxParser(fin, size)
	urn = p.c_string("utf-8")
	name = p.c_string("utf-8")
	return {"urn": urn, "name": name}, p.delta

def dref(fin, size, version, flags):  # needs to be parsed!!!
	p = BoxParser(fin, size)
	entry_count, = p.unpack(">L", 4)
	return {"entry_count": entry_count}, p.delta

def iinf(fin, size, version, flags):  # needs to be parsed!!!
	p = BoxParser(fin, size)
	if version == 0:
		entry_count, = p.unpack(">H", 2)
	elif version == 1:
		entry_count, = p.unpack(">L", 4)
	else:
		assert False

	return {"entry_count": entry_count}, p.delta

def pitm(fin, size, version, flags):
	""" Primary Item Box """

	p = BoxParser(fin, size)
	if version == 0:
		item_ID, = p.unpack(">H", 2)
	elif version == 1:
		item_ID, = p.unpack(">L", 4)
	else:
		assert False

	return {"item_ID": item_ID}, p.delta

def hdlr(fin, size, version, flags):
	assert version == 0

	p = BoxParser(fin, size)
	pre_defined, handler_type, reserved, reserved, reserved = p.unpack(">L4sLLL", 20)
	#assert pre_defined == 0
	name = p.c_string("utf-8")
	return {"handler_type": handler_type, "name": name}, p.delta

def tfdt(fin, size, version, flags):
	p = BoxParser(fin, size)
	if version == 0:
		baseMediaDecodeTime = p.unpack(">L", 4)
	elif version == 1:
		baseMediaDecodeTime = p.unpack(">Q", 8)

	return {"baseMediaDecodeTime": baseMediaDecodeTime}, p.delta

def frma(fin, size, version, flags):
	p = BoxParser(fin, size)
	data_format, = p.unpack(">4s", 4)

	return {"data_format": data_format}, p.delta

def schm(fin, size, version, flags):
	p = BoxParser(fin, size)

	scheme_type, scheme_version = p.unpack(">4sL", 8)
	ret = {"scheme_type": scheme_type, "scheme_version": scheme_version}
	if flags & 0x000001:
		scheme_uri = p.c_string()
		ret["scheme_uri"] = scheme_uri

	return ret, p.delta

def infe(fin, size, version, flags):
	p = BoxParser(fin, size)
	ret = {}
	if version in (0, 1):
		item_ID, item_protection_index = p.unpack(">HH", 4)
		ret["item_ID"] = item_ID
		ret["item_protection_index"] = item_protection_index

	#if version == 1:
	#	unsigned int(32) extension_type; //optional
	#	ItemInfoExtension(extension_type); //optional

	if version >= 2:
		if version == 2:
			item_ID, = p.unpack(">H", 2)
		elif version == 3:
			item_ID, = p.unpack(">L", 4)
		ret["item_ID"] = item_ID

		item_protection_index, item_type = p.unpack(">H4s", 6)
		ret["item_protection_index"] = item_protection_index
		ret["item_type"] = item_type

		item_name = p.c_string("utf-8")
		ret["item_name"] = item_name
		if item_type == b"mime":
			content_type = p.c_string("utf-8")
			ret["content_type"] = content_type
			#string content_encoding; //optional
		elif item_type == b"uri":
			item_uri_type = p.c_string("utf-8")
			ret["item_uri_type"] = item_uri_type

	return ret, p.delta

parsers = {
	"stsd": stsd,
	"iinf": iinf,
	"infe": infe,
	"pitm": pitm,
	"dref": dref,
	"url ": url,
	"urn ": urn,
	"hdlr": hdlr,
	"ftyp": ftyp,
	"dimg": dimg,
	"prft": prft,
	"tfdt": tfdt,
	"frma": frma,
	"schm": schm,
	"co64": co64,
	"stco": stco,
	"uuid": uuid,
	"ctts": ctts,
	"stsc": stsc,
	"stts": stts,
	"mfhd": mfhd,
	"fpar": fpar,
}

versions = {
	"iref": (0, 1),
	"meta": (0, ),
	"elng": (0, ),
	"stdp": (0, ),
	"fecr": (0, 1),
}

def _load_atoms():
	# type: () -> Dict[str, Tuple[str, str, str]]

	package_name = __package__ or "genutility"
	atoms_path = pkg_resources.resource_filename(package_name, "data/mp4-atoms.tsv")

	out = {}  # type: Dict[str, Tuple[str, str, str]]

	try:
		for fourcc, type, boxtype, description, _ in iter_csv(atoms_path, delimiter="\t", skip=1):
			assert fourcc not in out, fourcc
			out[fourcc] = (type, boxtype, description)
	except ValueError:
		logging.exception("Failed to parse atoms file at line %s", len(out) + 1)
		raise

	return out

atoms = _load_atoms()
atomcodep = re.compile(br"[0-9a-zA-Z ]{4}") # what do the specs say here?

def parse_atom(fin, code, size, version, flags):
	try:
		func = parsers[code]
		content, delta = func(fin, size, version, flags)
	except KeyError:
		content = {}
		delta = 0

	return content, delta

def read_atom(fin, parent_version=None):
	# type: (IO[bytes], Optional[int]) -> Tuple[int, str, int, int, dict]

	pos = fin.tell()

	p = BoxParser(fin)

	size, code = p.unpack(">L4s", 8)

	if not atomcodep.match(code):
		raise ParseError(f"{code!r} @ {pos} is not a valid atom code")

	code = code.decode("ascii") # cannot fail

	if size == 1: # 64bit size
		size, = p.unpack(">Q", 8)

	try:
		boxtype = atoms[code][1]
	except KeyError: # treat it as leaf and skip it
		boxtype = "box"
		warnings.warn(f"Unknown atom: '{code}'. Skipping...", stacklevel=2)

	if boxtype == "fullbox":
		version, flags = p.unpack(">B3s", 4)

		try:
			supported = versions[code]
			assert version in supported
		except KeyError:
			pass

	else:
		version = parent_version
		flags = None

	return pos, code, size, p.delta, version, flags

def _enum_atoms(fin, total_size, depth, parse_atoms=True, unparsed_data=False, version=None):
	# type: (IO[bytes], int, int, bool, bool, Optional[int]) -> Iterator[Tuple[int, int, str, int, Optional[bytes]]]

	while fin.tell() < total_size:
		pos, type, size, delta, version, flags = read_atom(fin, version)

		if parse_atoms:
			content, d = parse_atom(fin, type, size - delta, version, flags)
			delta += d
		else:
			content = None

		if size == 0:
			raise Break("Atom extends to the end of the file") # just stop parsing here

		atom_end = pos + size

		try:
			boxtype = atoms[type][0]
		except KeyError: # treat it as leaf and skip it
			boxtype = "leaf"
			warnings.warn(f"Unknown atom: '{type}'. Skipping...", stacklevel=2)

		if boxtype == "cont":
			yield depth, pos, type, size, content, None

			for atom in _enum_atoms(fin, atom_end, depth+1, parse_atoms, unparsed_data, version):
				yield atom
		elif boxtype == "leaf":
			if unparsed_data:
				leaf = fin.read(size - delta)
				yield depth, pos, type, size, content, leaf
			else:
				yield depth, pos, type, size, content, None
				fin.seek(atom_end, os.SEEK_SET)
		else:
			assert False

	if fin.tell() != total_size:
		raise ParseError(f"Invalid file structure. Possibly truncated. {fin.tell()}/{total_size}")

def enumerate_atoms(path, parse_atoms=False, unparsed_data=False):
	# type: (str, bool) -> Iterator[Tuple[int, int, str, int, Optional[bytes]]]

	""" Takes an ISO/IEC base media file format / mp4 file `path`
		and yields (depth, position, code, size, parsed_data, unparsed_data) tuples.
		Unknown atoms will print a warning.
	"""

	total_size = os.path.getsize(path)
	with open(path, "rb") as fr:
		try:
			for atom in _enum_atoms(fr, total_size, 0, parse_atoms, unparsed_data):
				yield atom
		except Break:
			pass
		except EOFError:
			raise ParseError("Truncated file.")

if __name__ == "__main__":

	from argparse import ArgumentParser
	from os import fspath
	from sys import stderr

	import pandas as pd

	from genutility.args import is_dir
	from genutility.filesystem import scandir_ext
	from genutility.iter import list_except, progress
	atoms_path = pkg_resources.resource_filename(__package__, "data/mp4-atoms.tsv")
	df = pd.read_csv(atoms_path, sep="\t")
	df.sort_values("fourcc").to_csv(atoms_path + ".new", sep="\t", index=False)

	def bytes_from_ascii(s):
		return s.encode("ascii")

	parser = ArgumentParser()
	parser.add_argument("path", type=is_dir)
	parser.add_argument("-e", "--errors-only", action="store_true")
	parser.add_argument("-r", "--recursive", action="store_true")
	parser.add_argument("--extensions", nargs="+", default=[".mp4", ".mov", ".f4v", ".heif", ".heic", ".3gp", ".3g2", ".mj2"])
	parser.add_argument("--type", nargs="+", help="Limit output to following types, or in comination with --errors-only only log errors if last tag is doesn't have this type.")
	parser.add_argument("--search", type=bytes_from_ascii)
	parser.add_argument("--no-parse-atoms", action="store_false")
	args = parser.parse_args()

	logging.basicConfig(level=logging.INFO)

	unparsed_data = args.search or args.type

	errors_count = 0
	total_count = 0
	for path in progress(scandir_ext(args.path, args.extensions, rec=args.recursive)):
		if args.errors_only:
			total_count += 1
			exc, res = list_except(enumerate_atoms(fspath(path), parse_atoms=args.no_parse_atoms))
			if exc:
				if args.type is None or (res and res[-1][2] not in args.type):
					for depth, pos, type, size, _, _ in res:
						print("--"*depth, pos, type, size, file=stderr)
					logging.exception("Enumerating atoms of %s failed", path, exc_info=exc)
					errors_count += 1
		else:
			print(path)
			for depth, pos, type, size, content, leaf in enumerate_atoms(fspath(path), parse_atoms=args.no_parse_atoms, unparsed_data=unparsed_data):
				if args.type and type in args.type:
					print("--"*depth, pos, type, size, content, leaf)
				elif args.search and leaf and args.search in leaf:
					print("--"*depth, pos, type, size, content, args.search)
				else:
					leavsize = len(leaf) if leaf else 0
					print("--"*depth, pos, type, size, content, leavsize)
			print()

	if args.errors_only:
		print(f"{errors_count}/{total_count} files failed to parse")
