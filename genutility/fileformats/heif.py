from ..exceptions import ParseError
from .isobmff import FileSlice, enumerate_atoms


class NoExifFound(Exception):
    pass


def _collect_metas(path):
    parents = []
    metas = []

    for depth, pos, type, _size, content, leaf in enumerate_atoms(path, parse_atoms=True):
        while parents and parents[-1][0] >= depth:
            parents.pop()
        parent_type = parents[-1][1] if parents else None
        meta = parents[-1][3] if parents else None
        if type == "meta":
            moof_pos = next((entry[2] for entry in reversed(parents) if entry[1] == "moof"), 0)
            meta = {
                "exif_ids": [],
                "items": {},
                "item_info": {},
                "idat": [],
                "iloc_refs": {},
                "cdsc_refs": {},
                "data_refs": [],
                "primary": None,
                "file_origin": moof_pos,
            }
            metas.append(meta)
        elif meta is not None:
            if parent_type == "dref":
                meta["data_refs"].append((type, content))
            if type == "infe" and "item_ID" in content:
                meta["item_info"][content["item_ID"]] = content
                if content.get("item_type") == b"Exif":
                    meta["exif_ids"].append(content["item_ID"])
            elif type == "pitm" and "item_ID" in content:
                meta["primary"] = content["item_ID"]
            elif type == "iloc":
                if "items" in content:
                    meta["items"].update((item["item_ID"], item) for item in content["items"])
                elif parent_type == "iref":
                    meta["iloc_refs"].setdefault(content["from_item_id"], []).extend(content["to_item_ids"])
            elif type == "cdsc" and parent_type == "iref":
                meta["cdsc_refs"].setdefault(content["from_item_id"], []).extend(content["to_item_ids"])
            elif type == "idat":
                meta["idat"].append((leaf.offset, leaf.size))
        parents.append((depth, type, pos, meta))

    return metas


def _read_extent(source, offset, length, extent_count):
    limit = len(source)
    if offset < 0 or offset > limit or length < 0:
        raise ValueError(f"Bad HEIF extent: offset={offset}, length={length}, limit={limit}")
    if length == 0:
        if extent_count != 1:
            raise ValueError("Bad HEIF extent: implicit length requires a single extent")
        length = limit - offset
    if length > limit - offset:
        raise ValueError(f"Bad HEIF extent: offset={offset}, length={length}, limit={limit}")

    if isinstance(source, bytes):
        data = source[offset : offset + length]
    else:
        source.seek(offset)
        data = source.read(length)
    if len(data) != length:
        raise ValueError(f"Truncated HEIF extent: expected {length} bytes, got {len(data)}")
    return data


def _read_item(fr, file_size, meta, item_id, active=(), cache=None):
    if item_id in active:
        raise ValueError("Cyclic HEIF item location")
    # ponytail: cap reference depth at 128; use an iterative resolver if deeper chains are needed.
    if len(active) >= 128:
        raise ValueError("HEIF item reference depth exceeds the supported limit of 128 items")
    # ISO 14496-12:2015, 8.11.3.1/8.11.6: interpret and slice only unprotected item data.
    if meta["item_info"].get(item_id, {}).get("item_protection_index", 0):
        raise ValueError("Protected HEIF items are not supported")
    if cache is None:
        cache = {}
    if item_id in cache:
        return cache[item_id]
    item = meta["items"].get(item_id)
    if item is None:
        raise ValueError("Bad file")
    method = item["construction_method"]
    if method in (None, 0):
        reference_index = item["data_reference_index"]
        if reference_index:
            if reference_index > len(meta["data_refs"]):
                raise ValueError("Bad HEIF data reference index")
            reference_type, reference = meta["data_refs"][reference_index - 1]
            if reference_type != "url " or not reference.get("self_contained"):
                raise ValueError("External HEIF item data references are not supported")
        origin = meta["file_origin"]
        source = FileSlice(fr, origin, file_size - origin)
    elif method == 1:
        if len(meta["idat"]) != 1:
            raise ValueError("Bad file")
        source = FileSlice(fr, *meta["idat"][0])
    elif method != 2:
        raise ValueError(f"Unsupported HEIF construction method: {method}")

    entries = item["entries"]
    data = []
    for entry in entries:
        if method == 2:
            references = meta["iloc_refs"].get(item_id, ())
            extent_index = getattr(entry, "extent_index", 1)
            if extent_index == 0 or extent_index > len(references):
                raise ValueError("Bad HEIF item-offset reference")
            source = _read_item(fr, file_size, meta, references[extent_index - 1], (*active, item_id), cache)
        offset = item["base_offset"] + entry.extent_offset
        data.append(_read_extent(source, offset, entry.extent_length, len(entries)))
    result = b"".join(data)
    cache[item_id] = result
    return result


def heif_get_exif(path: str) -> bytes:
    """Extract unprotected Exif TIFF data, following chains of at most 128 items.

    Unsupported protection or deeper item references raise ValueError.
    """

    metas = _collect_metas(path)
    with open(path, "rb") as fr:
        fr.seek(0, 2)
        file_size = fr.tell()

        for meta in metas:
            exif_ids = [item_id for item_id in meta["exif_ids"] if item_id in meta["items"]]
            if meta["primary"] is not None:
                exif_ids = [item_id for item_id in exif_ids if meta["primary"] in meta["cdsc_refs"].get(item_id, ())]
            if len(exif_ids) > 1:
                raise ValueError("Ambiguous HEIF Exif items")
            if not exif_ids:
                continue
            exif_data = _read_item(fr, file_size, meta, exif_ids[0])
            if len(exif_data) < 4:
                raise ValueError("Bad HEIF Exif item")
            tiff_offset = int.from_bytes(exif_data[:4], "big")
            tiff_start = 4 + tiff_offset
            if tiff_start >= len(exif_data):
                raise ValueError("Bad HEIF Exif TIFF header offset")
            return exif_data[tiff_start:]

    raise NoExifFound("No Exif info found")


if __name__ == "__main__":
    import logging
    from argparse import ArgumentParser
    from struct import error as StructError

    import piexif

    from genutility.args import is_dir

    logger = logging.getLogger(__name__)
    parser = ArgumentParser()
    parser.add_argument("path", type=is_dir)
    parser.add_argument("-r", "--recursive", action="store_true")
    args = parser.parse_args()

    if args.recursive:
        it = args.path.rglob("*.heic")
    else:
        it = args.path.glob("*.heic")

    for path in it:
        relpath = path.relative_to(args.path)

        try:
            data = heif_get_exif(path)
            exif = piexif.load(data)
            # CIPA DC-008-2023 Table 17 recommends these tags but does not require them.
            fields = (piexif.ImageIFD.Make, piexif.ImageIFD.Model, piexif.ImageIFD.DateTime)
            print(relpath, *(exif["0th"].get(tag, b"").decode("ascii", errors="replace") for tag in fields))
        except NoExifFound:
            logger.info("%s: No Exif Found", relpath)
        except (ParseError, ValueError, OSError, StructError):
            logger.exception(relpath)
