import logging
import os
import re
import struct
import warnings
from base64 import b64decode
from collections import namedtuple
from pathlib import Path
from typing import Any, Collection, Dict, Iterator, List, Literal, NamedTuple, Optional, Tuple, Union, cast

try:
    from importlib.resources import as_file, files
except ImportError:
    from importlib_resources import as_file, files  # type: ignore[no-redef]

from .._files import PathType
from ..csv import iter_csv
from ..exceptions import ParseError
from ..file import BufferedBinaryIoT, read_or_raise

logger = logging.getLogger(__name__)

Profile = Literal["auto", "isobmff", "quicktime"]
_PROFILES = {"auto", "isobmff", "quicktime"}


class FileSlice:
    """A seekable, lazy view of a byte range in an open file stream.

    The slice is only usable while its original stream remains open.
    """

    def __init__(self, fin: BufferedBinaryIoT, offset: int, size: int):
        self.fin = fin
        self.offset = offset
        self.size = size
        self._pos = 0

    def tell(self) -> int:
        return self._pos

    def seek(self, offset: int, whence: int = os.SEEK_SET) -> int:
        if whence == os.SEEK_SET:
            pos = offset
        elif whence == os.SEEK_CUR:
            pos = self._pos + offset
        elif whence == os.SEEK_END:
            pos = self.size + offset
        else:
            raise ValueError(f"Invalid whence: {whence}")
        if pos < 0:
            raise ValueError("Negative seek position")
        self._pos = pos
        return pos

    def read(self, size: int = -1) -> bytes:
        size = min(self.size - self._pos, size if size >= 0 else self.size - self._pos)
        if size <= 0:
            return b""
        pos = self.fin.tell()
        try:
            self.fin.seek(self.offset + self._pos)
            data = self.fin.read(size)
        finally:
            self.fin.seek(pos)
        self._pos += len(data)
        return data

    def contains(self, value: bytes, chunk_size: int = 65536) -> bool:
        if not value:
            return True
        pos = self.tell()
        overlap = b""
        try:
            self.seek(0)
            while True:
                chunk = self.read(chunk_size)
                if not chunk:
                    return False
                chunk = overlap + chunk
                if value in chunk:
                    return True
                overlap = chunk[-(len(value) - 1) :] if len(value) > 1 else b""
        finally:
            self.seek(pos)

    def __len__(self) -> int:
        return self.size

    def __bool__(self) -> bool:
        return self.size > 0

    def __repr__(self) -> str:
        return f"FileSlice(offset={self.offset}, size={self.size})"


# http://mp4ra.org/#/atoms
# https://wiki.multimedia.cx/index.php/QuickTime_container#QuickTime_Atom_Reference
# https://sno.phy.queensu.ca/~phil/exiftool/TagNames/QuickTime.html


class BoxParser:
    def __init__(self, fin: BufferedBinaryIoT, size: Optional[int] = None):
        self.fin = fin
        self.size = size
        self.delta = 0

    def unpack(self, format: str, size: int):
        if self.size is not None and (size < 0 or size > self.size - self.delta):
            raise ParseError("Atom parser read exceeds atom body")
        ret = struct.unpack(format, read_or_raise(self.fin, size))
        self.delta += size
        return ret

    @staticmethod
    def read_c_string(fin: BufferedBinaryIoT, size: int) -> bytes:
        ret: List[bytes] = []
        while len(ret) < size:
            c = fin.read(1)
            if not c:
                raise EOFError
            ret.append(c)
            if c == b"\0":
                return b"".join(ret)
        raise ParseError("Unterminated atom string")

    def c_string(self, encoding: Optional[str] = None) -> Union[bytes, str]:
        assert self.size is not None, "Size not specified"
        s = self.read_c_string(self.fin, self.size - self.delta)
        self.delta += len(s)
        s = s.rstrip(b"\0")
        if encoding is None:
            return s
        return self.decode_string(s, encoding)

    @staticmethod
    def decode_string(value: bytes, encoding: str) -> str:
        try:
            return value.decode(encoding)
        except UnicodeDecodeError:
            ret = value.decode("latin-1")
            logger.warning("'%s' is not a valid %s string", ret, encoding)
            return ret


def _unpack_named_batch(p: BoxParser, count: int, entry_format: str, length: int, named_tuple_cls: Any) -> List[tuple]:
    assert len(named_tuple_cls._fields) == length, "length parameter doesn't match named tuple size"
    size = count * struct.calcsize(entry_format)
    data = p.unpack(f">{size}s", size)[0] if size else b""
    return [named_tuple_cls._make(entry) for entry in struct.iter_unpack(entry_format, data)]


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


def fpar(fin: BufferedBinaryIoT, size: int, version: int, flags: bytes, strict: bool = False) -> Tuple[dict, int]:
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
    if strict and reserved != 0:
        raise ParseError("Reserved fpar field is not zero")

    scheme_specific_info = b64decode(p.c_string("ascii"))
    if version == 0:
        (entry_count,) = p.unpack(">H", 2)
    elif version == 1:
        (entry_count,) = p.unpack(">L", 4)

    entries = _unpack_named_batch(p, entry_count, ">HL", 2, FilePartitionEntry)
    return {
        "item_ID": item_ID,
        "packet_payload_size": packet_payload_size,
        "FEC_encoding_ID": FEC_encoding_ID,
        "FEC_instance_ID": FEC_instance_ID,
        "max_source_block_length": max_source_block_length,
        "encoding_symbol_length": encoding_symbol_length,
        "max_number_of_encoding_symbols": max_number_of_encoding_symbols,
        "scheme_specific_info": scheme_specific_info,
        "file_partition_entries": entries,
    }, p.delta


def iref_parser(fin, size, version, flags=None):
    p = BoxParser(fin, size)
    if version == 0:
        item_format, item_size = "H", 2
    elif version == 1:
        item_format, item_size = "L", 4
    else:
        raise ParseError(f"Unsupported version: {version}")

    (from_item_id,) = p.unpack(f">{item_format}", item_size)
    (to_item_ids_num,) = p.unpack(">H", 2)
    to_item_ids = p.unpack(f">{to_item_ids_num}{item_format}", to_item_ids_num * item_size)

    return {"from_item_id": from_item_id, "to_item_ids": to_item_ids}, p.delta


def trackref_parser(fin, size, version, flags=None):
    if size % 4:
        raise ParseError("Track reference size is not a multiple of four")
    p = BoxParser(fin, size)
    return {"track_IDs": p.unpack(f">{size // 4}L", size)}, p.delta


def ctts(fin: BufferedBinaryIoT, size: int, version: int, flags: bytes) -> Tuple[dict, int]:
    """Composition Time to Sample Box / CompositionOffsetBox"""
    p = BoxParser(fin, size)

    (entry_count,) = p.unpack(">L", 4)

    if version == 0:
        entry_format = ">LL"
    elif version == 1:
        entry_format = ">Ll"
    else:
        raise ParseError(f"Unsupported version: {version}")

    entries = _unpack_named_batch(p, entry_count, entry_format, 2, CompositionOffsetEntry)

    return {"composition_offset_entries": entries}, p.delta


def stsc(fin: BufferedBinaryIoT, size: int, version: int, flags: bytes) -> Tuple[dict, int]:
    """Sample To Chunk Box"""

    if version != 0:
        raise ParseError(f"Unsupported version: {version}")
    p = BoxParser(fin, size)
    (entry_count,) = p.unpack(">L", 4)
    entries = _unpack_named_batch(p, entry_count, ">LLL", 3, SampleToChunkEntry)
    return {"sample_to_chunk_entries": entries}, p.delta


def stts(fin: BufferedBinaryIoT, size: int, version: int, flags: bytes) -> Tuple[dict, int]:
    """TimeToSampleBox"""

    if version != 0:
        raise ParseError(f"Unsupported version: {version}")
    p = BoxParser(fin, size)
    (entry_count,) = p.unpack(">L", 4)
    entries = _unpack_named_batch(p, entry_count, ">LL", 2, TimeToSampleEntry)
    return {"time_to_samples_entries": entries}, p.delta


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


def schm(fin: BufferedBinaryIoT, size: int, version: int, flags: bytes) -> Tuple[dict, int]:
    p = BoxParser(fin, size)

    scheme_type, scheme_version = p.unpack(">4sL", 8)
    ret = {"scheme_type": scheme_type, "scheme_version": scheme_version}
    if int.from_bytes(flags, byteorder="big") & 0x000001:
        scheme_uri = p.c_string()
        ret["scheme_uri"] = scheme_uri

    return ret, p.delta


def url(fin: BufferedBinaryIoT, size: int, version: int, flags: bytes) -> Tuple[dict, int]:
    if int.from_bytes(flags, byteorder="big") & 1:
        return {"self_contained": True}, 0

    p = BoxParser(fin, size)
    return {"location": p.c_string("utf-8")}, p.delta


def hdlr(fin: BufferedBinaryIoT, size: int, version: int, flags: bytes) -> Tuple[dict, int]:
    p = BoxParser(fin, size)
    pre_defined, handler_type, _reserved_0, _reserved_1, _reserved_2 = p.unpack(">4s4s3L", 20)
    ret = {"handler_type": handler_type}
    if p.delta < size:
        # QTFF media/data handlers use counted names; metadata handlers use UTF-8 C strings.
        if pre_defined in (b"mhlr", b"dhlr"):
            (length,) = p.unpack(">B", 1)
            (name,) = p.unpack(f">{length}s", length)
            ret["name"] = p.decode_string(name, "utf-8")
        else:
            ret["name"] = p.c_string("utf-8")
    return ret, p.delta


def urn(fin: BufferedBinaryIoT, size: int, version: int, flags: bytes) -> Tuple[dict, int]:
    p = BoxParser(fin, size)
    ret = {"name": p.c_string("utf-8")}
    # ISO 14496-12:2015, 8.7.2.3 makes location optional despite the unconditional syntax.
    if p.delta < size:
        ret["location"] = p.c_string("utf-8")
    return ret, p.delta


def mvcg(fin: BufferedBinaryIoT, size: int, version: int, flags: bytes, strict: bool = False) -> Tuple[dict, int]:
    p = BoxParser(fin, size)
    multiview_group_id, num_entries = p.unpack(">LH", 6)
    (reserved,) = p.unpack(">B", 1)
    if strict and reserved != 0:
        raise ParseError("Reserved mvcg field is not zero")
    entries = []

    for _ in range(num_entries):
        (entry_type,) = p.unpack(">B", 1)
        entry = {"entry_type": entry_type}
        if entry_type == 0:
            (entry["track_id"],) = p.unpack(">L", 4)
        elif entry_type == 1:
            entry["track_id"], entry["tier_id"] = p.unpack(">LH", 6)
        elif entry_type == 2:
            (output_view_id,) = p.unpack(">H", 2)
            if strict and output_view_id & 0xFC00:
                raise ParseError("Reserved mvcg output_view_id bits are not zero")
            entry["output_view_id"] = output_view_id & 0x03FF
        elif entry_type == 3:
            start_view_id, view_count = p.unpack(">HH", 4)
            if strict and start_view_id & 0xFC00:
                raise ParseError("Reserved mvcg start_view_id bits are not zero")
            entry["start_view_id"] = start_view_id & 0x03FF
            entry["view_count"] = view_count
        else:
            raise ParseError(f"Unsupported mvcg entry type: {entry_type}")
        entries.append(entry)

    return {
        "multiview_group_id": multiview_group_id,
        "num_entries": num_entries,
        "entries": entries,
    }, p.delta


def infe(fin: BufferedBinaryIoT, size: int, version: int, flags: bytes) -> Tuple[dict, int]:
    if version not in (0, 1, 2, 3):
        raise ParseError(f"Unsupported version: {version}")

    p = BoxParser(fin, size)
    ret = {}
    if version in (0, 1):
        item_ID, item_protection_index = p.unpack(">HH", 4)
        ret["item_ID"] = item_ID
        ret["item_protection_index"] = item_protection_index
        ret["item_name"] = p.c_string("utf-8")
        ret["content_type"] = p.c_string("utf-8")
        remaining = size - p.delta
        if version == 0 and remaining:
            ret["content_encoding"] = p.c_string("utf-8")
        elif version == 1 and remaining:
            ret["content_encoding"] = p.c_string("utf-8")
            if p.delta + 4 <= size:
                (ret["extension_type"],) = p.unpack(">L", 4)

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
            if p.delta < size:
                ret["content_encoding"] = p.c_string("utf-8")
        elif item_type == b"uri ":
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


def iloc(fin: BufferedBinaryIoT, size: int, version: int, flags: bytes, strict: bool = False) -> Tuple[dict, int]:
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
        if strict and index_size_reserved != 0:
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
            reserved, construction_method = divmod(a, 16)
            if strict and reserved != 0:
                raise ParseError("Reserved iloc construction method field is not zero")
        else:
            construction_method = None

        if base_offset_size == 0:
            data_reference_index, extent_count = p.unpack(">HH", 4)
            base_offset = 0
        else:
            fmt_char = size_to_format_char(base_offset_size)
            data_reference_index, base_offset, extent_count = p.unpack(f">H{fmt_char}H", 4 + base_offset_size)

        entries: List[tuple] = []
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


def jp2_colr(fin: BufferedBinaryIoT, size: int, version: int, flags: bytes) -> Tuple[dict, int]:
    """ITU-T T.800:2002 I.5.3.3; preserve ICC bytes without interpreting the profile."""
    p = BoxParser(fin, size)
    method, precedence, approximation = p.unpack(">BbB", 3)
    fields: Dict[str, Any] = {"method": method, "precedence": precedence, "approximation": approximation}
    if method == 1:
        (fields["colourspace"],) = p.unpack(">I", 4)
    elif method == 2:
        remaining = size - p.delta
        (fields["icc_profile"],) = p.unpack(f">{remaining}s", remaining)
    # Other methods are opaque, as required by the JP2 specification.
    return fields, p.delta


_PARSERS = {
    func.__name__: func
    for func in (
        fpar,
        iref_parser,
        trackref_parser,
        ctts,
        stsc,
        stts,
        iinf,
        pitm,
        schm,
        url,
        urn,
        hdlr,
        mvcg,
        infe,
        iloc,
        jp2_colr,
    )
}
_ATOMS_RESOURCE = files("genutility.fileformats").joinpath("data", "isobmff-atoms.tsv")


class AtomDefinition(NamedTuple):
    profile: str
    parent: str
    grammar: str
    boxtype: str
    description: str
    spec: str
    parser: str
    versions: Tuple[int, ...]
    layout: Tuple[Tuple[str, str, Optional[str]], ...]


# An ilst key identifies a metadata item, regardless of any registered fourcc.
_METADATA_ITEM = AtomDefinition("*", "*", "item-content", "box", "Metadata item", "", "-", (), ())


def _parse_layout(value: str) -> Tuple[Tuple[str, str, Optional[str]], ...]:
    """Compile scalars, strings, packed languages, byte fields and counted/tail arrays."""

    if not value or value == "-":
        return ()

    operations = []
    fields = set()
    numeric_fields = set()
    tokens = value.split(",")
    for index, token in enumerate(tokens):
        match = re.fullmatch(r"([ui](?:8|16|32|64))(\?)?(?::([A-Za-z_]\w*))?", token)
        if match:
            optional = bool(match.group(2))
            if optional and index != len(tokens) - 1:
                raise ValueError("An optional scalar must be the last layout field")
            name = match.group(3)
            if name:
                if name in fields:
                    raise ValueError(f"Duplicate layout field: {name!r}")
                fields.add(name)
                numeric_fields.add(name)
            operations.append(("optional" if optional else "scalar", match.group(1), name))
            continue

        match = re.fullmatch(r"(cstring|text|language):([A-Za-z_]\w*)", token)
        if match:
            name = match.group(2)
            if name in fields:
                raise ValueError(f"Duplicate layout field: {name!r}")
            fields.add(name)
            operations.append((match.group(1), name, None))
            continue

        match = re.fullmatch(r"bytes\[(\d+|[A-Za-z_]\w*)\](?::([A-Za-z_]\w*))?", token)
        if match:
            count = match.group(1)
            if not count.isdecimal() and count not in numeric_fields:
                raise ValueError(f"Unknown layout field: {count!r}")
            name = match.group(2)
            if name:
                if name in fields:
                    raise ValueError(f"Duplicate layout field: {name!r}")
                fields.add(name)
            operations.append(("bytes", count, name))
            continue

        match = re.fullmatch(r"(u8|u16|u32|u64|i8|i16|i32|i64|fourcc)\[([A-Za-z_]\w*)?\](?::([A-Za-z_]\w*))?", token)
        if match:
            count = match.group(2) or ""
            if count and count not in numeric_fields:
                raise ValueError(f"Unknown layout field: {count!r}")
            if not count and index != len(tokens) - 1:
                raise ValueError("A tail array must be the last layout field")
            name = match.group(3)
            if name:
                if name in fields:
                    raise ValueError(f"Duplicate layout field: {name!r}")
                fields.add(name)
            operations.append(("array", f"{match.group(1)}:{count}", name))
            continue

        raise ValueError(f"Invalid layout token: {token!r}")

    return tuple(operations)


def _parse_versions(value: str) -> Tuple[int, ...]:
    return tuple(int(item) for item in value.split(",") if item) if value and value != "-" else ()


def _load_atoms() -> Dict[str, List[AtomDefinition]]:
    out: Dict[str, List[AtomDefinition]] = {}

    with as_file(_ATOMS_RESOURCE) as atoms_path:
        try:
            for row in iter_csv(os.fspath(atoms_path), delimiter="\t", skip=1):
                if len(row) == 9:
                    # Keep the common no-layout rows compact in the TSV.
                    row.append("-")
                if len(row) == 10:
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
                        layout,
                    ) = row
                else:
                    raise ValueError(f"Expected 10 columns, got {len(row)}")

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
                        _parse_layout(layout),
                    )
                )
        except ValueError:
            logger.exception("Failed to parse atoms file at line %s", len(out) + 1)
            raise

    return out


atom_variants = _load_atoms()
printable_atomcodep = re.compile(rb"[ -~\xa0-\xff]{4}")


def _atom_definition(
    code: str, profile: Profile, parent: Optional[str], version: Optional[int] = None
) -> Optional[AtomDefinition]:
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
        if version is not None and definition.versions and version not in definition.versions:
            continue
        version_score = int(bool(definition.versions)) if version is not None else 0
        candidates.append((profile_score, parent_score, version_score, definition))

    if not candidates:
        return None

    best_score = max(
        (parent_score, profile_score, version_score) for profile_score, parent_score, version_score, _ in candidates
    )
    best = [
        definition
        for profile_score, parent_score, version_score, definition in candidates
        if (parent_score, profile_score, version_score) == best_score
    ]
    if len(best) > 1:
        if version is None and len({(definition.grammar, definition.boxtype) for definition in best}) == 1:
            return best[0]
        raise ParseError(f"Ambiguous atom definition for {code!r}")
    return best[0]


def _validate_profile(profile: str) -> None:
    if profile not in _PROFILES:
        raise ValueError(f"Unsupported profile: {profile!r}")


def _printable_atom_code(code: bytes) -> bool:
    return printable_atomcodep.fullmatch(code) is not None


def _looks_like_atom_header(fin: BufferedBinaryIoT, offset: int, remaining: int) -> bool:
    if remaining - offset < 8:
        return False

    pos = fin.tell()
    try:
        fin.seek(pos + offset, os.SEEK_SET)
        header = fin.read(8)
        if len(header) != 8:
            return False

        size, _code = struct.unpack(">L4s", header)
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
    return grammar == "item-content" or grammar.startswith(("container", "entry-list", "item-list", "sample-entry:"))


def _layout_is_plausible(fin: BufferedBinaryIoT, body_size: int, definition: AtomDefinition) -> bool:
    """Check a table-described container header without knowing its fourcc."""

    if not _is_container_grammar(definition.grammar):
        return True
    if definition.boxtype == "?":
        return _looks_like_atom_header(fin, 0, body_size) or _looks_like_atom_header(fin, 4, body_size)
    if definition.boxtype == "fullbox" and definition.versions and body_size >= 4:
        pos = fin.tell()
        try:
            version = read_or_raise(fin, 1)[0]
        finally:
            fin.seek(pos, os.SEEK_SET)
        if version not in definition.versions:
            return True  # Unrecognized versions are opaque; their child layout is unknown.
    offset = 4 if definition.boxtype == "fullbox" else 0
    return _looks_like_atom_header(fin, offset, body_size)


def _resolve_boxtype(fin: BufferedBinaryIoT, body_size: int, definition: AtomDefinition) -> str:
    if definition.boxtype != "?" or not _is_container_grammar(definition.grammar):
        return "box" if definition.boxtype == "?" else definition.boxtype

    box = _looks_like_atom_header(fin, 0, body_size)
    fullbox = _looks_like_atom_header(fin, 4, body_size)
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

    definitions = [definition for definition in atom_variants.get(code, ()) if _definition_matches(definition, parent)]
    if any(definition.parent == parent for definition in definitions):
        definitions = [definition for definition in definitions if definition.parent == parent]
    definitions = [definition for definition in definitions if definition.profile in {"isobmff", "quicktime"}]
    profiles = {definition.profile for definition in definitions}
    if len(profiles) <= 1:
        return cast(Profile, next(iter(profiles), "auto"))

    plausible = {definition.profile for definition in definitions if _layout_is_plausible(fin, body_size, definition)}
    if len(plausible) == 1:
        return cast(Profile, next(iter(plausible)))
    if len(plausible) > 1:
        raise ParseError(f"Ambiguous atom profile for {code!r}; specify profile='isobmff' or profile='quicktime'")
    raise ParseError(f"Cannot determine atom profile for {code!r}; specify profile='isobmff' or profile='quicktime'")


def _parser_for(definition: Optional[AtomDefinition], code: str):
    parser_name = definition.parser if definition is not None else code.rstrip()
    if not parser_name or parser_name == "-":
        return None
    return _PARSERS.get(parser_name)


def parse_atom(
    fin: BufferedBinaryIoT,
    code: str,
    size: int,
    version: Optional[int],
    flags: bytes,
    definition: Optional[AtomDefinition] = None,
    strict: bool = False,
) -> Tuple[dict, int]:
    func = _parser_for(definition, code)
    if func is None:
        return {}, 0
    if func in (fpar, iloc, mvcg):
        return func(fin, size, version, flags, strict=strict)
    return func(fin, size, version, flags)


def _consume_sample_entry_prefix(
    fin: BufferedBinaryIoT,
    remaining: int,
    grammar: str,
    parent_version: Optional[int],
    media_handler: Optional[bytes] = None,
) -> Tuple[dict, int]:
    """Read the shared sample-entry fields before any extension child boxes."""

    kind = grammar[len("sample-entry:") :]
    if kind == "media":
        # 'raw ' is shared by QuickTime video and PCM audio. Isolated MJ2 entries default to audio.
        kind = "visual" if media_handler == b"vide" else "audio"
    if kind == "visual":
        prefix_size = 78  # SampleEntry (8) + VisualSampleEntry (70)
    elif kind == "hint":
        # SampleEntry (8) + HintSampleEntry (hint version, compatible version, max packet size)
        prefix_size = 16
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
    data = read_or_raise(fin, prefix_size)
    fields = {"data_reference_index": int.from_bytes(data[6:8], "big")}
    if kind == "visual":
        fields["width"], fields["height"] = struct.unpack(">HH", data[24:28])
    elif kind == "audio":
        fields["audio_version"] = version
        if version != 2:
            fields["channel_count"], fields["sample_size"] = struct.unpack(">HH", data[16:20])
            fields["sample_rate_fixed"] = int.from_bytes(data[24:28], "big")
    return fields, prefix_size


def _consume_layout(
    fin: BufferedBinaryIoT,
    remaining: int,
    layout: Tuple[Tuple[str, str, Optional[str]], ...],
) -> Tuple[Dict[str, Any], int]:
    """Consume table-described fields before children or across a leaf payload."""

    values: Dict[str, Any] = {}
    consumed = 0

    def skip(count: int) -> None:
        nonlocal consumed
        if count < 0 or count > remaining - consumed:
            raise ParseError("Atom layout exceeds atom body")
        pos = fin.tell()
        fin.seek(0, os.SEEK_END)
        if count > fin.tell() - pos:
            raise ParseError("Truncated atom layout")
        fin.seek(pos + count, os.SEEK_SET)
        consumed += count

    for operation, argument, name in layout:
        if operation in ("scalar", "optional"):
            if operation == "optional" and consumed == remaining:
                continue
            size = int(argument[1:]) // 8
            if size > remaining - consumed:
                raise ParseError("Atom layout exceeds atom body")
            value = int.from_bytes(read_or_raise(fin, size), byteorder="big", signed=argument.startswith("i"))
            consumed += size
            if name:
                values[name] = value
        elif operation == "cstring":
            string_bytes = bytearray()
            while consumed < remaining:
                char = read_or_raise(fin, 1)
                consumed += 1
                if char == b"\0":
                    break
                string_bytes.extend(char)
            else:
                raise ParseError("Unterminated atom-layout string")
            try:
                values[argument] = string_bytes.decode("utf-8")
            except UnicodeDecodeError:
                values[argument] = string_bytes.decode("latin-1")
                logger.warning("'%s' is not a valid utf-8 string", values[argument])
        elif operation == "language":
            if remaining - consumed < 2:
                raise ParseError("Atom layout exceeds atom body")
            packed = int.from_bytes(read_or_raise(fin, 2), "big")
            consumed += 2
            letters = [(packed >> shift) & 31 for shift in (10, 5, 0)]
            if packed & 0x8000 or any(not 1 <= letter <= 26 for letter in letters):
                raise ParseError("Invalid packed language code")
            values[argument] = "".join(chr(letter + 0x60) for letter in letters)
        elif operation == "text":
            # 3GPP TS 26.244: UTF-16 text starts with a BOM and has a two-byte terminator.
            pos = fin.tell()
            marker = fin.read(min(2, remaining - consumed))
            fin.seek(pos)
            utf16 = marker in (b"\xfe\xff", b"\xff\xfe")
            width = 2 if utf16 else 1
            data = bytearray()
            while remaining - consumed >= width:
                char = read_or_raise(fin, width)
                consumed += width
                if char == b"\0" * width:
                    break
                data.extend(char)
            else:
                raise ParseError("Unterminated metadata text")
            try:
                values[argument] = data.decode("utf-16" if utf16 else "utf-8")
            except UnicodeDecodeError:
                raise ParseError("Invalid metadata text encoding") from None
        elif operation == "bytes":
            try:
                count = int(argument) if argument.isdecimal() else values[argument]
            except KeyError:
                raise ParseError(f"Atom layout references an unknown field: {argument!r}") from None
            if not isinstance(count, int):
                raise ParseError(f"Atom layout field {argument!r} is not an integer")
            if name:
                if count < 0 or count > remaining - consumed:
                    raise ParseError("Atom layout exceeds atom body")
                values[name] = read_or_raise(fin, count)
                consumed += count
            else:
                skip(count)
        elif operation == "array":
            scalar_type, count_field = argument.split(":", 1)
            scalar_width = 4 if scalar_type == "fourcc" else int(scalar_type[1:]) // 8
            if count_field:
                try:
                    count = values[count_field]
                except KeyError:
                    raise ParseError(f"Atom layout references an unknown field: {count_field!r}") from None
            else:
                count, partial = divmod(remaining - consumed, scalar_width)
                if partial:
                    raise ParseError("Atom tail array has a partial element")
            if not isinstance(count, int):
                raise ParseError(f"Atom layout field {count_field!r} is not an integer")
            byte_count = count * scalar_width
            if name:
                if count < 0 or byte_count > remaining - consumed:
                    raise ParseError("Atom layout exceeds atom body")
                format_code = {
                    "u8": "B",
                    "u16": "H",
                    "u32": "I",
                    "u64": "Q",
                    "i8": "b",
                    "i16": "h",
                    "i32": "i",
                    "i64": "q",
                    "fourcc": "4s",
                }[scalar_type]
                fmt = ">" + ("4s" * count if scalar_type == "fourcc" else str(count) + format_code)
                values[name] = struct.unpack(fmt, read_or_raise(fin, byte_count))
                consumed += byte_count
            else:
                skip(byte_count)
        else:
            raise AssertionError(f"Invalid atom-layout operation: {operation!r}")

        if consumed > remaining:
            raise ParseError("Atom layout exceeds atom body")

    return values, consumed


def read_atom(
    fin: BufferedBinaryIoT,
    container_end: int,
    depth: int,
    parent_version: Optional[int] = None,
    profile: Profile = "auto",
    parent_type: Optional[str] = None,
    parent_grammar: Optional[str] = None,
) -> Tuple[int, str, int, int, Optional[int], bytes, Profile, Optional[AtomDefinition]]:
    _validate_profile(profile)
    pos = fin.tell()

    p = BoxParser(fin)

    if container_end - pos < 8:
        raise ParseError(f"Truncated atom header at {pos}")
    size, code = p.unpack(">L4s", 8)

    item_list = (parent_grammar or "").startswith("item-list")
    numeric_item = item_list and not _printable_atom_code(code)

    if numeric_item:
        code = str(int.from_bytes(code, byteorder="big"))
    else:
        code = code.decode("latin-1")

    if size == 1:  # 64bit size
        if container_end - pos < 16:
            raise ParseError(f"Truncated extended atom header at {pos}")
        (size,) = p.unpack(">Q", 8)
    elif size == 0:
        if depth != 0 and profile == "quicktime":
            raise ParseError("Only a top-level atom may have size 0")
        # ISO 14496-12:2015, 4.2: size zero extends to file EOF, even when nested.
        fin.seek(0, os.SEEK_END)
        size = fin.tell() - pos
        fin.seek(pos + p.delta, os.SEEK_SET)

    if size < p.delta or size > container_end - pos:
        raise ParseError(f"Invalid atom size {size} at {pos}")
    p.size = size

    if item_list:
        effective_profile, definition = profile, _METADATA_ITEM
    else:
        effective_profile = _resolve_profile(fin, code, size - p.delta, profile, parent_type)
        definition = _atom_definition(code, effective_profile, parent_type)

    boxtype = _resolve_boxtype(fin, size - p.delta, definition) if definition is not None else "box"
    if boxtype == "fullbox":
        version, flags = p.unpack(">B3s", 4)
        # ISO 14496-12:2015, 4.2 requires unrecognized versions to be skipped.
        definition = _atom_definition(code, effective_profile, parent_type, version)
    else:
        version = parent_version
        flags = b""

    return pos, code, size, p.delta, version, flags, effective_profile, definition


def _enum_atoms(
    fin: BufferedBinaryIoT,
    total_size: int,
    depth: int,
    parse_atoms: bool = True,
    version: Optional[int] = None,
    profile: Profile = "auto",
    parent_type: Optional[str] = None,
    parent_grammar: Optional[str] = None,
    strict: bool = False,
    media_handler: Optional[bytes] = None,
) -> Iterator[Tuple[int, int, str, int, Optional[dict], Optional[FileSlice]]]:
    if depth > 128 and fin.tell() < total_size:
        raise ParseError("Atom nesting exceeds the limit of 128")
    content: Optional[dict]
    while fin.tell() < total_size:
        if parent_grammar == "container:zero-terminator" and profile != "isobmff" and total_size - fin.tell() == 4:
            # QTFF p. 48 permits exactly one final uint32 zero in a user-data list.
            if read_or_raise(fin, 4) != b"\0" * 4:
                raise ParseError("Invalid user-data terminator")
            break
        if (parent_grammar or "").startswith("sample-entry:") and total_size - fin.tell() < 8:
            fin.seek(total_size, os.SEEK_SET)
            break

        pos, type, size, delta, atom_version, flags, effective_profile, definition = read_atom(
            fin, total_size, depth, version, profile, parent_type, parent_grammar
        )

        if parent_type == "mdia" and type == "hdlr" and definition is not None and size - delta >= 8:
            # QTFF requires the media handler before minf. Peek only the fixed fields so raw
            # traversal preserves its payload slice; minf/meta data handlers do not change it.
            handler_start = fin.tell()
            fin.seek(handler_start + 4, os.SEEK_SET)
            media_handler = read_or_raise(fin, 4)
            fin.seek(handler_start, os.SEEK_SET)

        if not parse_atoms and depth == 0 and type == "ftyp" and definition is not None:
            # Validate the declaration in raw mode while retaining its unparsed payload slice.
            layout_start = fin.tell()
            _consume_layout(fin, size - delta, definition.layout)
            fin.seek(layout_start, os.SEEK_SET)

        if definition is None and not (parent_grammar or "").startswith(("item-list", "item-content", "entry-list")):
            warnings.warn(f"Unknown or unsupported atom: '{type}'. Skipping...", stacklevel=2)
        container = definition is not None and _is_container_grammar(definition.grammar)

        parser = _parser_for(definition, type)
        strict_validation = strict and parser in (fpar, iloc)
        if parse_atoms or (container and parser is not None) or strict_validation:
            parse_start = fin.tell()
            if definition is None:
                content, d = {}, 0
            else:
                content, d = parse_atom(fin, type, size - delta, atom_version, flags, definition, strict)
            delta += d
            if not parse_atoms and strict_validation:
                fin.seek(parse_start, os.SEEK_SET)
                delta -= d
        else:
            content = None

        if definition is not None and definition.grammar.startswith("sample-entry:"):
            sample_fields, sample_size = _consume_sample_entry_prefix(
                fin, size - delta, definition.grammar, atom_version, media_handler
            )
            delta += sample_size
            if parse_atoms:
                content = dict(content or {}, **sample_fields)

        if (
            definition is not None
            and definition.layout
            and (container or parse_atoms or definition.boxtype == "uuidbox")
        ):
            layout_fields, layout_size = _consume_layout(fin, size - delta, definition.layout)
            delta += layout_size
            if (parse_atoms or container) and layout_fields:
                content = dict(content or {})
                content.update((name, value) for name, value in layout_fields.items() if not name.startswith("_"))

        atom_end = pos + size

        if container:
            yield depth, pos, type, size, content if parse_atoms else None, None

            entry_count = 0
            grammar = cast(AtomDefinition, definition).grammar
            entry_type = grammar.partition(":")[2] if grammar.startswith("entry-list:") else None
            for child in _enum_atoms(
                fin,
                atom_end,
                depth + 1,
                parse_atoms,
                atom_version,
                effective_profile,
                type,
                grammar,
                strict,
                None if type == "mdia" else media_handler,
            ):
                if child[0] == depth + 1 and (not entry_type or child[2] == entry_type):
                    entry_count += 1
                yield child
            if grammar.startswith("entry-list"):
                expected_count = (content or {}).get("entry_count")
                if entry_count != expected_count:
                    raise ParseError(f"{type} declares {expected_count} entries, found {entry_count}")
        else:
            leaf = FileSlice(fin, fin.tell(), size - delta)
            yield depth, pos, type, size, content if parse_atoms else None, leaf
            fin.seek(atom_end, os.SEEK_SET)

    if fin.tell() != total_size:
        raise ParseError(f"Invalid file structure. Possibly truncated. {fin.tell()}/{total_size}")


def _file_profile(fin: BufferedBinaryIoT, total_size: int) -> Profile:
    """Find a top-level ftyp without inspecting other boxes' dialect-specific contents."""

    pos = fin.tell()
    try:
        while total_size - fin.tell() >= 8:
            start = fin.tell()
            size, code = struct.unpack(">I4s", read_or_raise(fin, 8))
            header_size = 8
            if size == 1:
                if total_size - fin.tell() < 8:
                    break
                (size,) = struct.unpack(">Q", read_or_raise(fin, 8))
                header_size = 16
            elif size == 0:
                size = total_size - start
            if size < header_size or size > total_size - start:
                break  # Normal traversal reports invalid framing and preserves its yielded prefix.
            if code == b"ftyp":
                definition = cast(AtomDefinition, _atom_definition("ftyp", "auto", None))
                try:
                    fields, _ = _consume_layout(fin, size - header_size, definition.layout)
                except ParseError:
                    # The declaration exists; validate it during traversal, without structural fallback.
                    return "isobmff"
                brands = (fields["major_brand"], *fields["compatible_brands"])
                return "quicktime" if b"qt  " in brands else "isobmff"
            fin.seek(start + size, os.SEEK_SET)
        return "auto"
    finally:
        fin.seek(pos, os.SEEK_SET)


def enumerate_atoms(
    path: PathType,
    parse_atoms: bool = False,
    profile: Profile = "auto",
    strict: bool = False,
) -> Iterator[Tuple[int, int, str, int, Optional[dict], Optional[FileSlice]]]:
    """Read ISO base media boxes (MP4, 3GP, 3G2, MJ2, HEIF) or QuickTime atoms
    and yields (depth, position, code, size, parsed_data, data) tuples. Leaf
    data is a lazy, seekable `FileSlice` bounded to the atom's unparsed payload;
    container data is `None`. Read a leaf slice before the iterator is exhausted
    or closed, because its underlying file is closed when iteration ends.
    `profile` may be `"isobmff"`, `"quicktime"`, or `"auto"`; auto resolves
    the top-level `ftyp` brands first: `qt  ` selects QuickTime, otherwise ISO.
    Only files without `ftyp` use structural detection of profile variants.
    An explicit profile overrides the declaration.
    `strict` enables additional specification-conformance checks that are not
    required to parse the file (currently, reserved-field checks). These checks
    are disabled by default; structural checks needed for parsing, such as atom
    size validation, always run.
    Box identifiers are unrestricted four-byte values. Unknown atoms and
    unrecognized box versions are opaque and print a warning, except inside
    metadata item lists/content and counted entry lists, where unknown entries
    are left opaque without warnings.
    Container nesting is limited to 128 levels. This reads container metadata,
    not compressed media or whole-file format conformance.
    """

    _validate_profile(profile)
    total_size = os.path.getsize(path)
    with open(path, "rb") as fr:
        try:
            if profile == "auto":
                profile = _file_profile(fr, total_size)
            yield from _enum_atoms(fr, total_size, 0, parse_atoms, profile=profile, strict=strict)
        except EOFError:
            raise ParseError("Truncated file.") from None


if __name__ == "__main__":
    from argparse import ArgumentParser
    from os import fspath
    from sys import stderr

    from rich.progress import Progress as RichProgress

    from genutility.filesystem import scandir_ext
    from genutility.iter import list_except
    from genutility.rich import Progress

    def bytes_from_ascii(s):
        return s.encode("ascii")

    parser = ArgumentParser()
    parser.add_argument("path", type=Path, help="Input file or directory")
    parser.add_argument("-e", "--errors-only", action="store_true")
    parser.add_argument("-r", "--recursive", action="store_true")
    parser.add_argument(
        "--extensions",
        nargs="+",
        default=[".mp4", ".mov", ".f4v", ".heif", ".heic", ".avif", ".3gp", ".3g2", ".mj2", ".mjp2"],
    )
    parser.add_argument(
        "--type",
        nargs="+",
        help="Show only these atom types. With --errors-only, suppress errors after these atom types.",
    )
    parser.add_argument("--search", type=bytes_from_ascii)
    parser.add_argument("--no-parse-atoms", action="store_false")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    if not args.path.exists():
        raise FileNotFoundError(fspath(args.path))

    def print_atoms(
        path: PathType, parse_atoms: bool, only_type: Optional[Collection[str]], search: Optional[bytes]
    ) -> None:
        for depth, pos, type, size, content, leaf in enumerate_atoms(fspath(path), parse_atoms=parse_atoms):
            if only_type and type not in only_type:
                continue
            if only_type:
                print("--" * depth, pos, type, size, content, leaf.read() if leaf else None)
            elif search and leaf and leaf.contains(search):
                print("--" * depth, pos, type, size, content, search)
            else:
                leavsize = len(leaf) if leaf else 0
                print("--" * depth, pos, type, size, content, leavsize)

    def print_atoms_error_only(path: PathType, parse_atoms: bool, only_type: Optional[Collection[str]]) -> bool:
        exc, res = list_except(enumerate_atoms(fspath(path), parse_atoms=parse_atoms))
        if exc and not (only_type and res and res[-1][2] in only_type):
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
