import logging
import os
import re
import struct
import warnings
from base64 import b64decode
from collections import namedtuple
from pathlib import Path
from typing import Any, Collection, Dict, Iterable, Iterator, List, Literal, NamedTuple, Optional, Tuple, Union

try:
    from importlib.resources import as_file, files
except ImportError:
    from importlib_resources import as_file, files

from ..csv import iter_csv
from ..exceptions import Break, ParseError
from ..file import BufferedBinaryIoT, read_or_raise
from ..iter import batch

logger = logging.getLogger(__name__)

Profile = Literal["auto", "isobmff", "quicktime"]
_PROFILES = {"auto", "isobmff", "quicktime"}

# http://mp4ra.org/#/atoms
# https://wiki.multimedia.cx/index.php/QuickTime_container#QuickTime_Atom_Reference
# https://sno.phy.queensu.ca/~phil/exiftool/TagNames/QuickTime.html

class BoxParser:
    def __init__(self, fin: BufferedBinaryIoT, size: Optional[int] = None):
        self.fin = fin
        self.size = size
        self.delta = 0

    def unpack(self, format: str, size: int):
        ret = struct.unpack(format, read_or_raise(self.fin, size))
        self.delta += size
        return ret

    @staticmethod
    def read_c_string(fin: BufferedBinaryIoT, size: int) -> bytes:
        ret: List[bytes] = []
        while len(ret) < size:
            c = fin.read(1)
            ret.append(c)
            if c == b"\0":
                break
        return b"".join(ret)

    def c_string(self, encoding: Optional[str] = None) -> Union[bytes, str]:
        assert self.size is not None, "Size not specified"
        s = self.read_c_string(self.fin, self.size - self.delta)
        self.delta += len(s)
        s = s.rstrip(b"\0")
        if encoding is None:
            return s
        else:
            try:
                return s.decode(encoding)
            except UnicodeDecodeError:
                ret = s.decode("latin-1")  # should never fail
                logger.warning("'%s' is not a valid %s string", ret, encoding)
                return ret


def named_batch(entries: Iterable, length: int, named_tuple_cls: object) -> List[tuple]:
    assert len(named_tuple_cls._fields) == length, "length parameter doesn't match named tuple size"
    return list(batch(entries, length, named_tuple_cls._make))


# named tuples


class SampleToChunkEntry(NamedTuple):
    first_chunk: int
    samples_per_chunk: int
    sample_description_index: int


class CompositionOffsetEntry(NamedTuple):
    sample_count: int
    sample_offset: int


class TimeToSampleEntry(NamedTuple):
    sample_count: int
    sample_delta: int


class FilePartitionEntry(NamedTuple):
    block_count: int
    block_size: int


ItemLocationEntryWithIndex = namedtuple(
    "ItemLocationEntryWithIndex", ["extent_index", "extent_offset", "extent_length"]
)
ItemLocationEntry = namedtuple("ItemLocationEntry", ["extent_offset", "extent_length"])

# atoms


def stco(fin: BufferedBinaryIoT, size: int, version: int, flags: bytes) -> Tuple[dict, int]:
    """ChunkOffsetBox"""

    if version != 0:
        raise ParseError(f"Unsupported version: {version}")
    p = BoxParser(fin, size)

    (entry_count,) = p.unpack(">L", 4)
    chunk_offsets = p.unpack(f">{entry_count}L", entry_count * 4)

    return {"chunk_offsets": chunk_offsets}, p.delta


def fpar(fin: BufferedBinaryIoT, size: int, version: int, flags: bytes) -> Tuple[dict, int]:
    """FilePartitionBox"""

    if version not in (0, 1):
        raise ParseError(f"Unsupported version: {version}")
    p = BoxParser(fin, size)

    if version == 0:
        (item_ID,) = p.unpack(">H", 2)
    elif version == 1:
        (item_ID,) = p.unpack(">L", 4)

    (
        packet_payload_size,
        reserved,
        FEC_encoding_ID,
        FEC_instance_ID,
        max_source_block_length,
        encoding_symbol_length,
        max_number_of_encoding_symbols,
    ) = p.unpack(">H2B4H", 12)
    if reserved != 0:
        raise ParseError("Reserved fpar field is not zero")

    scheme_specific_info = b64decode(p.c_string("ascii"))
    if version == 0:
        (entry_count,) = p.unpack(">H", 2)
    elif version == 1:
        (entry_count,) = p.unpack(">L", 4)

    entries = p.unpack(f">{'HL' * entry_count}", entry_count * 6)
    return {
        "item_ID": item_ID,
        "packet_payload_size": packet_payload_size,
        "FEC_encoding_ID": FEC_encoding_ID,
        "FEC_instance_ID": FEC_instance_ID,
        "max_source_block_length": max_source_block_length,
        "encoding_symbol_length": encoding_symbol_length,
        "max_number_of_encoding_symbols": max_number_of_encoding_symbols,
        "scheme_specific_info": scheme_specific_info,
        "file_partition_entries": named_batch(entries, 2, FilePartitionEntry),
    }, p.delta


def mfhd(fin: BufferedBinaryIoT, size: int, version: int, flags: bytes) -> Tuple[dict, int]:
    """MovieFragmentHeaderBox"""

    if version != 0:
        raise ParseError(f"Unsupported version: {version}")
    p = BoxParser(fin, size)

    (sequence_number,) = p.unpack(">L", 4)

    return {"sequence_number": sequence_number}, p.delta


def co64(fin: BufferedBinaryIoT, size: int, version: int, flags: bytes) -> Tuple[dict, int]:
    if version != 0:
        raise ParseError(f"Unsupported version: {version}")
    p = BoxParser(fin, size)

    (entry_count,) = p.unpack(">L", 4)
    chunk_offsets = p.unpack(f">{entry_count}Q", entry_count * 8)

    return {"chunk_offsets": chunk_offsets}, p.delta


def prft(fin: BufferedBinaryIoT, size: int, version: int, flags: bytes) -> Tuple[dict, int]:
    p = BoxParser(fin, size)

    if version == 0:
        reference_track_ID, ntp_timestamp, media_time = p.unpack(">LQL", 16)
    elif version == 1:
        reference_track_ID, ntp_timestamp, media_time = p.unpack(">LQQ", 20)
    else:
        raise ParseError(f"Unsupported version: {version}")

    return {"reference_track_ID": reference_track_ID, "ntp_timestamp": ntp_timestamp, "media_time": media_time}, p.delta


def iref_parser(fin, size, version):
    p = BoxParser(fin, size)
    if version == 0:
        (from_item_id,) = p.unpack(">H", 2)
    elif version == 1:
        (from_item_id,) = p.unpack(">L", 4)
    else:
        raise ParseError(f"Unsupported version: {version}")

    if size == p.delta:  # empty box, found in test files, is this standard?
        to_item_ids = ()
    else:
        (to_item_ids_num,) = p.unpack(">H", 2)

        if version == 0:
            to_item_ids = p.unpack(f">{to_item_ids_num}H", to_item_ids_num * 2)
        elif version == 1:
            to_item_ids = p.unpack(f">{to_item_ids_num}L", to_item_ids_num * 4)
        else:
            raise ParseError(f"Unsupported version: {version}")

    return {"from_item_id": from_item_id, "to_item_ids": to_item_ids}, p.delta


def dimg(fin: BufferedBinaryIoT, size: int, version: int, flags: bytes) -> Tuple[dict, int]:
    """Not a fullbox, inherits parent version"""

    return iref_parser(fin, size, version)


def thmb(fin: BufferedBinaryIoT, size: int, version: int, flags: bytes) -> Tuple[dict, int]:
    """Not a fullbox, inherits parent version"""

    return iref_parser(fin, size, version)


def cdsc(fin: BufferedBinaryIoT, size: int, version: int, flags: bytes) -> Tuple[dict, int]:
    """Not a fullbox, inherits parent version"""

    return iref_parser(fin, size, version)


def ctts(fin: BufferedBinaryIoT, size: int, version: int, flags: bytes) -> Tuple[dict, int]:
    """Composition Time to Sample Box / CompositionOffsetBox"""
    p = BoxParser(fin, size)

    (entry_count,) = p.unpack(">L", 4)

    if version == 0:
        entries = p.unpack(f">{entry_count * 2}L", entry_count * 2 * 4)
    elif version == 1:
        entries = p.unpack(f">{'Ll' * entry_count}", entry_count * 2 * 4)
    else:
        raise ParseError(f"Unsupported version: {version}")

    return {"composition_offset_entries": named_batch(entries, 2, CompositionOffsetEntry)}, p.delta


def stsc(fin: BufferedBinaryIoT, size: int, version: int, flags: bytes) -> Tuple[dict, int]:
    """Sample To Chunk Box"""

    if version != 0:
        raise ParseError(f"Unsupported version: {version}")
    p = BoxParser(fin, size)
    (entry_count,) = p.unpack(">L", 4)
    entries = p.unpack(f">{entry_count * 3}L", entry_count * 3 * 4)
    return {"sample_to_chunk_entries": named_batch(entries, 3, SampleToChunkEntry)}, p.delta


def stts(fin: BufferedBinaryIoT, size: int, version: int, flags: bytes) -> Tuple[dict, int]:
    """TimeToSampleBox"""

    if version != 0:
        raise ParseError(f"Unsupported version: {version}")
    p = BoxParser(fin, size)
    (entry_count,) = p.unpack(">L", 4)
    entries = p.unpack(f">{entry_count * 2}L", entry_count * 2 * 4)
    return {"time_to_samples_entries": named_batch(entries, 2, TimeToSampleEntry)}, p.delta


def uuid(fin: BufferedBinaryIoT, size: int, version: int, flags: bytes) -> Tuple[dict, int]:
    p = BoxParser(fin, size)
    (uuid,) = p.unpack(">16s", 16)
    return {"uuid": uuid}, p.delta


def ftyp(fin: BufferedBinaryIoT, size: int, version: int, flags: bytes) -> Tuple[dict, int]:
    p = BoxParser(fin, size)
    major_brand, minor_version = p.unpack(">4sL", 8)
    return {"major_brand": major_brand, "minor_version": minor_version}, p.delta


def stsd(fin: BufferedBinaryIoT, size: int, version: int, flags: bytes) -> Tuple[dict, int]:
    if version not in (0, 1):
        raise ParseError(f"Unsupported version: {version}")
    p = BoxParser(fin, size)
    (entry_count,) = p.unpack(">L", 4)
    return {"entry_count": entry_count}, p.delta


def url(fin: BufferedBinaryIoT, size: int, version: int, flags: bytes) -> Tuple[dict, int]:
    if version != 0:
        raise ParseError(f"Unsupported version: {version}")
    p = BoxParser(fin, size)
    url = p.c_string("utf-8")
    return {"url": url}, p.delta


def urn(fin: BufferedBinaryIoT, size: int, version: int, flags: bytes) -> Tuple[dict, int]:
    if version != 0:
        raise ParseError(f"Unsupported version: {version}")
    p = BoxParser(fin, size)
    urn = p.c_string("utf-8")
    name = p.c_string("utf-8")
    return {"urn": urn, "name": name}, p.delta


def dref(fin: BufferedBinaryIoT, size: int, version: int, flags: bytes) -> Tuple[dict, int]:  # needs to be parsed!!!
    p = BoxParser(fin, size)
    (entry_count,) = p.unpack(">L", 4)
    return {"entry_count": entry_count}, p.delta


def iinf(fin: BufferedBinaryIoT, size: int, version: int, flags: bytes) -> Tuple[dict, int]:  # needs to be parsed!!!
    p = BoxParser(fin, size)
    if version == 0:
        (entry_count,) = p.unpack(">H", 2)
    elif version == 1:
        (entry_count,) = p.unpack(">L", 4)
    else:
        raise ParseError(f"Unsupported version: {version}")

    return {"entry_count": entry_count}, p.delta


def pitm(fin: BufferedBinaryIoT, size: int, version: int, flags: bytes) -> Tuple[dict, int]:
    """Primary Item Box"""

    p = BoxParser(fin, size)
    if version == 0:
        (item_ID,) = p.unpack(">H", 2)
    elif version == 1:
        (item_ID,) = p.unpack(">L", 4)
    else:
        raise ParseError(f"Unsupported version: {version}")

    return {"item_ID": item_ID}, p.delta


def hdlr(fin: BufferedBinaryIoT, size: int, version: int, flags: bytes) -> Tuple[dict, int]:
    if version != 0:
        raise ParseError(f"Unsupported version: {version}")

    p = BoxParser(fin, size)
    _pre_defined, handler_type, _reserved1, _reserved2, _reserved3 = p.unpack(">L4sLLL", 20)
    # assert pre_defined == 0
    name = p.c_string("utf-8")
    return {"handler_type": handler_type, "name": name}, p.delta


def tfdt(fin: BufferedBinaryIoT, size: int, version: int, flags: bytes) -> Tuple[dict, int]:
    p = BoxParser(fin, size)
    if version == 0:
        (baseMediaDecodeTime,) = p.unpack(">L", 4)
    elif version == 1:
        (baseMediaDecodeTime,) = p.unpack(">Q", 8)
    else:
        raise ParseError(f"Unsupported version: {version}")

    return {"baseMediaDecodeTime": baseMediaDecodeTime}, p.delta


def frma(fin: BufferedBinaryIoT, size: int, version: int, flags: bytes) -> Tuple[dict, int]:
    p = BoxParser(fin, size)
    (data_format,) = p.unpack(">4s", 4)

    return {"data_format": data_format}, p.delta


def schm(fin: BufferedBinaryIoT, size: int, version: int, flags: bytes) -> Tuple[dict, int]:
    p = BoxParser(fin, size)

    scheme_type, scheme_version = p.unpack(">4sL", 8)
    ret = {"scheme_type": scheme_type, "scheme_version": scheme_version}
    if int.from_bytes(flags, byteorder="big") & 0x000001:
        scheme_uri = p.c_string()
        ret["scheme_uri"] = scheme_uri

    return ret, p.delta


def infe(fin: BufferedBinaryIoT, size: int, version: int, flags: bytes) -> Tuple[dict, int]:
    p = BoxParser(fin, size)
    ret = {}
    if version in (0, 1):
        item_ID, item_protection_index = p.unpack(">HH", 4)
        ret["item_ID"] = item_ID
        ret["item_protection_index"] = item_protection_index

    # if version == 1:
    #     unsigned int(32) extension_type; //optional
    #     ItemInfoExtension(extension_type); //optional

    if version >= 2:
        if version == 2:
            (item_ID,) = p.unpack(">H", 2)
        elif version == 3:
            (item_ID,) = p.unpack(">L", 4)
        ret["item_ID"] = item_ID

        item_protection_index, item_type = p.unpack(">H4s", 6)
        ret["item_protection_index"] = item_protection_index
        ret["item_type"] = item_type

        item_name = p.c_string("utf-8")
        ret["item_name"] = item_name
        if item_type == b"mime":
            content_type = p.c_string("utf-8")
            ret["content_type"] = content_type
            # string content_encoding; //optional
        elif item_type == b"uri":
            item_uri_type = p.c_string("utf-8")
            ret["item_uri_type"] = item_uri_type

    return ret, p.delta


def size_to_format_char(size: int) -> str:
    try:
        return {4: "L", 8: "Q"}[size]
    except KeyError:
        raise ParseError(f"Unsupported field size: {size}") from None


def unpack_sized(p: BoxParser, size: int) -> int:
    if size == 0:
        return 0
    (value,) = p.unpack(f">{size_to_format_char(size)}", size)
    return value


def iloc(fin: BufferedBinaryIoT, size: int, version: int, flags: bytes) -> Tuple[dict, int]:
    p = BoxParser(fin, size)
    ret: Dict[str, Any] = {}

    if version not in (0, 1, 2):
        raise ParseError(f"Unsupported version: {version}")

    # assert fin.tell() % 8 == 0

    a, b = p.unpack(">BB", 2)
    offset_size, length_size = divmod(a, 16)
    base_offset_size, index_size_reserved = divmod(b, 16)

    if version == 1 or version == 2:
        index_size = index_size_reserved
    else:
        if index_size_reserved != 0:
            raise ParseError("Reserved iloc field is not zero")
        index_size = 0

    for field_size in (offset_size, length_size, base_offset_size, index_size):
        if field_size not in (0, 4, 8):
            raise ParseError(f"Unsupported iloc field size: {field_size}")

    if version < 2:
        (item_count,) = p.unpack(">H", 2)
    elif version == 2:
        (item_count,) = p.unpack(">L", 4)

    ret["items"] = []

    for _i in range(item_count):
        if version < 2:
            (item_ID,) = p.unpack(">H", 2)
        elif version == 2:
            (item_ID,) = p.unpack(">L", 4)

        if version == 1 or version == 2:
            (a,) = p.unpack(">H", 2)
            _reserved, construction_method = divmod(a, 16)
        else:
            construction_method = None

        if base_offset_size == 0:
            data_reference_index, extent_count = p.unpack(">HH", 4)
            base_offset = 0
        else:
            fmt_char = size_to_format_char(base_offset_size)
            data_reference_index, base_offset, extent_count = p.unpack(f">H{fmt_char}H", 4 + base_offset_size)

        entries = []
        for _j in range(extent_count):
            if (version == 1 or version == 2) and index_size > 0:
                extent_index = unpack_sized(p, index_size)
                extent_offset = unpack_sized(p, offset_size)
                extent_length = unpack_sized(p, length_size)
                entries.append(ItemLocationEntryWithIndex(extent_index, extent_offset, extent_length))
            else:
                extent_offset = unpack_sized(p, offset_size)
                extent_length = unpack_sized(p, length_size)
                entries.append(ItemLocationEntry(extent_offset, extent_length))

        ret["items"].append(
            {
                "item_ID": item_ID,
                "construction_method": construction_method,
                "data_reference_index": data_reference_index,
                "base_offset": base_offset,
                "entries": entries,
            }
        )

    return ret, p.delta


_ATOMS_RESOURCE = files(__package__).joinpath("data", "mp4-atoms.tsv")

AtomDefinition = NamedTuple(
    "AtomDefinition",
    [
        ("profile", str),
        ("parent", str),
        ("grammar", str),
        ("boxtype", str),
        ("description", str),
        ("spec", str),
        ("parser", str),
        ("versions", Tuple[int, ...]),
    ],
)

def _parse_versions(value: str) -> Tuple[int, ...]:
    return tuple(int(item) for item in value.split(",") if item) if value and value != "-" else ()


def _load_atoms() -> Dict[str, List[AtomDefinition]]:
    out: Dict[str, List[AtomDefinition]] = {}

    with as_file(_ATOMS_RESOURCE) as atoms_path:
        try:
            for row in iter_csv(os.fspath(atoms_path), delimiter="\t", skip=1):
                if len(row) == 9:
                    (
                        fourcc,
                        grammar,
                        boxtype,
                        description,
                        spec,
                        profile,
                        parent,
                        parser,
                        supported_versions,
                    ) = row
                else:
                    raise ValueError(f"Expected 9 columns, got {len(row)}")

                out.setdefault(fourcc, []).append(
                    AtomDefinition(
                        profile,
                        parent,
                        grammar,
                        boxtype,
                        description,
                        spec,
                        parser.rstrip(),
                        _parse_versions(supported_versions),
                    )
                )
        except ValueError:
            logger.exception("Failed to parse atoms file at line %s", len(out) + 1)
            raise

    return out


atom_variants = _load_atoms()
atomcodep = re.compile(rb"[\x00-\xff]{4}")
printable_atomcodep = re.compile(rb"[ -~\xa0-\xff]{4}")
isobmff_atomcodep = re.compile(rb"[ -~]{4}")


def _atom_definition(code: str, profile: Profile, parent: Optional[str]) -> Optional[AtomDefinition]:
    definitions = atom_variants.get(code, ())
    candidates = []
    for definition in definitions:
        if definition.profile == profile:
            profile_score = 2
        elif definition.profile == "*":
            profile_score = 1
        elif profile == "auto" and definition.profile in _PROFILES - {"auto"}:
            profile_score = 0
        else:
            continue

        if definition.parent == parent:
            parent_score = 2
        elif definition.parent == "*":
            parent_score = 1
        else:
            continue
        candidates.append((profile_score, parent_score, definition))

    if not candidates:
        return None

    best_score = max((parent_score, profile_score) for profile_score, parent_score, _ in candidates)
    best = [definition for profile_score, parent_score, definition in candidates if (parent_score, profile_score) == best_score]
    if len(best) > 1:
        raise ParseError(f"Ambiguous atom definition for {code!r}; specify profile or parent")
    return best[0]


def _validate_profile(profile: str) -> None:
    if profile not in _PROFILES:
        raise ValueError(f"Unsupported profile: {profile!r}")


def _valid_atom_code(code: bytes, profile: Profile) -> bool:
    pattern = isobmff_atomcodep if profile == "isobmff" else atomcodep
    return pattern.fullmatch(code) is not None


def _printable_atom_code(code: bytes) -> bool:
    return printable_atomcodep.fullmatch(code) is not None


def _looks_like_atom_header(fin: BufferedBinaryIoT, offset: int, remaining: int, profile: Profile) -> bool:
    if remaining - offset < 8:
        return False

    pos = fin.tell()
    try:
        fin.seek(pos + offset, os.SEEK_SET)
        header = fin.read(8)
        if len(header) != 8:
            return False

        size, code = struct.unpack(">L4s", header)
        if not _valid_atom_code(code, profile):
            return False
        if size == 0:
            return False
        if size == 1:
            if remaining - offset < 16:
                return False
            extended_size_bytes = fin.read(8)
            if len(extended_size_bytes) != 8:
                return False
            (size,) = struct.unpack(">Q", extended_size_bytes)
            return 16 <= size <= remaining - offset
        return 8 <= size <= remaining - offset
    finally:
        fin.seek(pos, os.SEEK_SET)


def _definition_matches(definition: AtomDefinition, parent: Optional[str]) -> bool:
    return definition.parent in ("*", parent)


def _is_container_grammar(grammar: str) -> bool:
    return grammar in {"container", "entry-list"} or grammar.startswith(("item-list", "sample-entry:"))


def _layout_is_plausible(fin: BufferedBinaryIoT, body_size: int, definition: AtomDefinition) -> bool:
    """Check a table-described container header without knowing its fourcc."""

    if not _is_container_grammar(definition.grammar):
        return True
    if definition.boxtype == "?":
        return _looks_like_atom_header(fin, 0, body_size, "auto") or _looks_like_atom_header(fin, 4, body_size, "auto")
    offset = 4 if definition.boxtype == "fullbox" else 0
    return _looks_like_atom_header(fin, offset, body_size, "auto")


def _resolve_boxtype(fin: BufferedBinaryIoT, body_size: int, definition: AtomDefinition) -> str:
    if definition.boxtype != "?" or not _is_container_grammar(definition.grammar):
        return "box" if definition.boxtype == "?" else definition.boxtype

    box = _looks_like_atom_header(fin, 0, body_size, "auto")
    fullbox = _looks_like_atom_header(fin, 4, body_size, "auto")
    if fullbox and not box:
        return "fullbox"
    if box and not fullbox:
        return "box"
    if box and fullbox:
        raise ParseError("Ambiguous Box/FullBox layout; table header must be specified")
    raise ParseError("Cannot determine Box/FullBox layout from container contents")


def _resolve_profile(
    fin: BufferedBinaryIoT, code: str, body_size: int, profile: Profile, parent: Optional[str]
) -> Profile:
    if profile != "auto":
        return profile

    definitions = [
        definition
        for definition in atom_variants.get(code, ())
        if _definition_matches(definition, parent) and definition.profile in {"isobmff", "quicktime"}
    ]
    profiles = {definition.profile for definition in definitions}
    if len(profiles) <= 1:
        return next(iter(profiles), "auto")

    plausible = {
        definition.profile
        for definition in definitions
        if _layout_is_plausible(fin, body_size, definition)
    }
    if len(plausible) == 1:
        return next(iter(plausible))
    if len(plausible) > 1:
        raise ParseError(f"Ambiguous atom profile for {code!r}; specify profile='isobmff' or profile='quicktime'")
    raise ParseError(f"Cannot determine atom profile for {code!r}; specify profile='isobmff' or profile='quicktime'")


def _parser_for(definition: Optional[AtomDefinition], code: str):
    parser_name = definition.parser if definition is not None else code.rstrip()
    if not parser_name or parser_name == "-":
        return None
    func = globals().get(parser_name)
    return func if callable(func) else None


def parse_atom(
    fin: BufferedBinaryIoT,
    code: str,
    size: int,
    version: int,
    flags: bytes,
    definition: Optional[AtomDefinition] = None,
) -> Tuple[dict, int]:
    func = _parser_for(definition, code)
    if func is None:
        return {}, 0
    return func(fin, size, version, flags)


def _consume_sample_entry_prefix(
    fin: BufferedBinaryIoT, remaining: int, grammar: str, parent_version: Optional[int]
) -> int:
    """Advance over the fixed sample-entry fields described by the table."""

    kind = grammar[len("sample-entry:") :]
    if kind == "visual":
        prefix_size = 78  # SampleEntry (8) + VisualSampleEntry (70)
    elif kind == "audio":
        if remaining < 28:
            raise ParseError("Truncated audio sample entry")
        pos = fin.tell()
        fin.seek(pos + 8)
        (version,) = struct.unpack(">H", read_or_raise(fin, 2))
        fin.seek(pos)
        if version == 1 and parent_version == 1:
            # ISO AudioSampleEntryV1 keeps the 28-byte fixed prefix; child boxes follow it.
            prefix_size = 28
        else:
            # QuickTime SoundSampleDescription version 1/2 extends the fixed prefix.
            prefix_size = {0: 28, 1: 44, 2: 64}.get(version)
        if prefix_size is None:
            raise ParseError(f"Unsupported audio sample entry version: {version}")
    else:
        raise ParseError(f"Unsupported sample-entry grammar: {grammar!r}")

    if remaining < prefix_size:
        raise ParseError("Truncated sample entry")
    fin.seek(fin.tell() + prefix_size, os.SEEK_SET)
    return prefix_size


def read_atom(
    fin: BufferedBinaryIoT,
    parent_version: Optional[int] = None,
    profile: Profile = "auto",
    parent_type: Optional[str] = None,
    parent_grammar: Optional[str] = None,
) -> Tuple[int, str, int, int, Optional[int], bytes, Profile, Optional[AtomDefinition]]:
    _validate_profile(profile)
    pos = fin.tell()

    p = BoxParser(fin)

    size, code = p.unpack(">L4s", 8)

    item_list = (parent_grammar or "").startswith("item-list")
    item_code = item_list and (profile != "isobmff" or not _valid_atom_code(code, "isobmff"))
    numeric_item = item_code and not _printable_atom_code(code)
    if not _valid_atom_code(code, profile) and not item_code:
        raise ParseError(f"{code!r} @ {pos} is not a valid atom code")

    if numeric_item:
        code = str(int.from_bytes(code, byteorder="big"))
    else:
        code = code.decode("latin-1")

    if size == 1:  # 64bit size
        (size,) = p.unpack(">Q", 8)

    effective_profile = _resolve_profile(fin, code, size - p.delta, profile, parent_type)
    definition = _atom_definition(code, effective_profile, parent_type)

    boxtype = _resolve_boxtype(fin, size - p.delta, definition) if definition is not None else "box"
    if boxtype == "fullbox":
        version, flags = p.unpack(">B3s", 4)
        if definition.versions and version not in definition.versions:
            raise ParseError(f"Unsupported version for {code}: {version}")
    else:
        version = parent_version
        flags = b""

    return pos, code, size, p.delta, version, flags, effective_profile, definition


def _enum_atoms(
    fin: BufferedBinaryIoT,
    total_size: int,
    depth: int,
    parse_atoms: bool = True,
    unparsed_data: bool = False,
    version: Optional[int] = None,
    profile: Profile = "auto",
    parent_type: Optional[str] = None,
    parent_grammar: Optional[str] = None,
) -> Iterator[Tuple[int, int, str, int, Optional[dict], Optional[bytes]]]:
    while fin.tell() < total_size:
        if (parent_grammar or "").startswith("sample-entry:") and total_size - fin.tell() < 8:
            fin.seek(total_size, os.SEEK_SET)
            break

        pos, type, size, delta, version, flags, effective_profile, definition = read_atom(
            fin, version, profile, parent_type, parent_grammar
        )

        if size == 0:
            if depth != 0:
                raise ParseError("Only a top-level atom may have size 0")
            raise Break("Atom extends to the end of the file")  # just stop parsing here
        if size < delta:
            raise ParseError(f"Invalid atom size {size} at {pos}")

        if definition is None:  # treat it as a payload and skip it
            boxtype = "leaf"
            if not (parent_grammar or "").startswith(("item-list", "item-content", "entry-list")):
                warnings.warn(f"Unknown atom: '{type}'. Skipping...", stacklevel=2)
        else:
            boxtype = "cont" if _is_container_grammar(definition.grammar) else "leaf"

        # An item-list child is a metadata item whose payload is itself a
        # sequence of boxes.  The parent grammar, not each vendor item code,
        # describes that framing.
        if (parent_grammar or "").startswith("item-list"):
            boxtype = "cont"

        if parse_atoms or (boxtype == "cont" and _parser_for(definition, type) is not None):
            content, d = parse_atom(fin, type, size - delta, version, flags, definition)
            delta += d
            if not parse_atoms:
                content = None
        else:
            content = None

        if definition is not None and definition.grammar.startswith("sample-entry:"):
            delta += _consume_sample_entry_prefix(fin, size - delta, definition.grammar, version)

        atom_end = pos + size

        if boxtype == "cont":
            yield depth, pos, type, size, content, None

            child_grammar = (
                "item-content"
                if (parent_grammar or "").startswith("item-list")
                else definition.grammar if definition is not None else None
            )

            yield from _enum_atoms(
                fin,
                atom_end,
                depth + 1,
                parse_atoms,
                unparsed_data,
                version,
                effective_profile,
                type,
                child_grammar,
            )
        elif boxtype == "leaf":
            if unparsed_data:
                leaf = fin.read(size - delta)
                yield depth, pos, type, size, content, leaf
            else:
                yield depth, pos, type, size, content, None
                fin.seek(atom_end, os.SEEK_SET)
        else:
            assert False, "Invalid boxtype"

    if fin.tell() != total_size:
        raise ParseError(f"Invalid file structure. Possibly truncated. {fin.tell()}/{total_size}")


def enumerate_atoms(
    path: str, parse_atoms: bool = False, unparsed_data: bool = False, profile: Profile = "auto"
) -> Iterator[Tuple[int, int, str, int, Optional[dict], Optional[bytes]]]:
    """Takes an ISO/IEC base media file format, QuickTime, or MP4 file `path`
    and yields (depth, position, code, size, parsed_data, unparsed_data) tuples.
    `profile` may be `"isobmff"`, `"quicktime"`, or `"auto"`; auto resolves
    table-declared profile variants from their box layout when possible.
    Unknown atoms will print a warning.
    """

    _validate_profile(profile)
    total_size = os.path.getsize(path)
    with open(path, "rb") as fr:
        try:
            yield from _enum_atoms(fr, total_size, 0, parse_atoms, unparsed_data, profile=profile)
        except Break:
            pass
        except EOFError:
            raise ParseError("Truncated file.") from None


if __name__ == "__main__":
    from argparse import ArgumentParser
    from os import fspath
    from sys import stderr

    import pandas as pd
    from rich.progress import Progress as RichProgress

    from genutility.filesystem import scandir_ext
    from genutility.iter import list_except
    from genutility.rich import Progress

    with as_file(_ATOMS_RESOURCE) as atoms_path:
        df = pd.read_csv(atoms_path, sep="\t")
        df.sort_values("fourcc").to_csv(f"{atoms_path}.new", sep="\t", index=False)

    def bytes_from_ascii(s):
        return s.encode("ascii")

    parser = ArgumentParser()
    parser.add_argument("path", type=Path, help="Input file or directory")
    parser.add_argument("-e", "--errors-only", action="store_true")
    parser.add_argument("-r", "--recursive", action="store_true")
    parser.add_argument(
        "--extensions", nargs="+", default=[".mp4", ".mov", ".f4v", ".heif", ".heic", ".3gp", ".3g2", ".mj2"]
    )
    parser.add_argument(
        "--type",
        nargs="+",
        help="Limit output to following types, or in comination with --errors-only only log errors if last tag is doesn't have this type.",
    )
    parser.add_argument("--search", type=bytes_from_ascii)
    parser.add_argument("--no-parse-atoms", action="store_false")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    if not args.path.exists():
        raise FileNotFoundError(fspath(args.path))

    def print_atoms(path: Path, parse_atoms: bool, only_type: Collection[str], search: bytes) -> None:
        unparsed_data = bool(search) or bool(only_type)

        for depth, pos, type, size, content, leaf in enumerate_atoms(
            fspath(path), parse_atoms=parse_atoms, unparsed_data=unparsed_data
        ):
            if only_type and type in only_type:
                print("--" * depth, pos, type, size, content, leaf)
            elif search and leaf and search in leaf:
                print("--" * depth, pos, type, size, content, search)
            else:
                leavsize = len(leaf) if leaf else 0
                print("--" * depth, pos, type, size, content, leavsize)

    def print_atoms_error_only(path: Path, parse_atoms: bool, only_type: Collection[str]) -> bool:
        exc, res = list_except(enumerate_atoms(fspath(path), parse_atoms=parse_atoms))
        if exc:
            if only_type is None or (res and res[-1][2] not in only_type):
                for depth, pos, type, size, _, _ in res:
                    print("--" * depth, pos, type, size, file=stderr)
                logger.exception("Enumerating atoms of %s failed", path, exc_info=exc)
                return True
        return False

    with RichProgress() as progress:
        p = Progress(progress)

        if args.path.is_file():
            if args.errors_only:
                print_atoms_error_only(args.path, args.no_parse_atoms, args.type)
            else:
                print_atoms(args.path, args.no_parse_atoms, args.type, args.search)

        elif args.path.is_dir():
            errors_count = 0
            total_count = 0
            for path in p.track(scandir_ext(args.path, args.extensions, rec=args.recursive)):
                if args.errors_only:
                    total_count += 1
                    errors_count += int(print_atoms_error_only(path, args.no_parse_atoms, args.type))
                else:
                    print(path)
                    print_atoms(path, args.no_parse_atoms, args.type, args.search)
                    print()

            if args.errors_only:
                print(f"{errors_count}/{total_count} files failed to parse")

        else:
            assert False, "Not file or directory"
