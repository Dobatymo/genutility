import binascii
import gzip
import logging
from hashlib import sha1
from itertools import chain, compress, repeat, zip_longest
from os import fspath
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Union

import bencodepy
import requests

from .exceptions import ParseError, assert_choice
from .file import blockfileiter, blockfilesiter
from .filesystem import FileProperties, long_path_support

logger = logging.getLogger(__name__)

BENCODE_BINARY = bencodepy.Bencode(
    encoding=None,
    encoding_fallback=None,
    dict_ordered=False,
    dict_ordered_sort=False,
)
BENCODE_UTF8 = bencodepy.Bencode(encoding="utf-8", encoding_fallback="value", dict_ordered=True, dict_ordered_sort=True)


def read_torrent(path: Path, binary: bool = True) -> dict:
    with path.open("rb") as fr:
        if binary:
            return BENCODE_BINARY.decode(fr.read())
        else:
            return BENCODE_UTF8.decode(fr.read())


def write_torrent(data: dict, path: Path) -> None:
    with path.open("wb") as fw:
        fw.write(BENCODE_BINARY.encode(data))


def iterdecode(items: Iterable[Union[str, bytes]], encoding: str = "latin1") -> Iterator[str]:
    for item in items:
        if isinstance(item, str):
            yield item
        elif isinstance(item, bytes):
            yield item.decode(encoding)
        else:
            raise TypeError(f"items must be strings or bytes, not {type(item)}")


def read_torrent_info_dict(path: Path, normalize_string_fields: bool = False) -> dict:
    if normalize_string_fields:
        info = read_torrent(path, binary=False)["info"]
    else:
        info = read_torrent(path, binary=True)[b"info"]

    if normalize_string_fields:
        if isinstance(info["name"], bytes):
            try:
                info["name"] = info["name.utf-8"]
                del info["name.utf-8"]
                assert isinstance(info["name"], str)
            except KeyError:
                info["name"] = info["name"].decode("latin1")

        try:
            files = info["files"]
        except KeyError:
            pass
        else:
            for fd in files:
                if any(isinstance(p, bytes) for p in fd["path"]):
                    try:
                        fd["path"] = fd["path.utf-8"]
                        del fd["path.utf-8"]
                        assert all(isinstance(p, str) for p in fd["path"])
                    except KeyError:
                        fd["path"] = iterdecode(fd["path"])

    return info


def iter_torrent(path: Path) -> Iterator[FileProperties]:
    """Returns file informations from a torrent file.
    Hash (SHA-1) is obtained according to BEP0047 (if available).
    """

    """ *.utf-8 are hacks used by some clients to add utf-8 encoded strings.
        Now every string should be utf-8 encoded anyway, but in ancient times the encoding was not specified.
    """

    info = read_torrent_info_dict(path, normalize_string_fields=True)

    try:
        files = info["files"]
    except KeyError:
        yield FileProperties(info["name"], info["length"], False, hash=info.get("sha1"))
    else:
        for fd in files:
            yield FileProperties(info["name"] + "/" + "/".join(fd["path"]), fd["length"], False, hash=fd.get("sha1"))


def iter_fastresume(path: Path) -> Iterator[FileProperties]:
    """Files management in libtorrent fastresume files works like this (I think):
    - mapped_files contains a list with new files names, the list is truncated if the tail does not contain renamed files.
    - file_priority contains priorities for each file. Priority 0 means not downloaded.
    """

    try:
        d = read_torrent(path, binary=False)
    except bencodepy.BencodeDecodeError as e:
        logger.warning("%s: %s", path, e)
        raise

    save_path = Path(d["qBt-savePath"])
    save_path_ = Path(d["save_path"])
    assert save_path == save_path_, f"{save_path}, {save_path_}"

    path_torrent = Path(path).with_suffix(".torrent")
    try:
        files = list(iter_torrent(path_torrent))
    except bencodepy.BencodeDecodeError as e:
        logger.warning("%s: %s", path_torrent, e)
        raise

    # file_priority is truncated, remainder should be filled with 1
    file_priority: List[int] = d.get("file_priority", [])
    assert len(file_priority) <= len(files)
    file_priority = list(chain(file_priority, repeat(1, len(files) - len(file_priority))))

    # mapped_files is truncated, remainder should be filled with ""
    mapped_files: List[str] = d.get("mapped_files", [])
    assert len(mapped_files) <= len(files)

    it = compress(zip_longest(files, mapped_files), file_priority)
    for file, mapped_file in it:
        if not mapped_file:  # either None from zip_longest, or "" as placeholder in fastresume file
            file.abspath = long_path_support(fspath(save_path / file.relpath))
        else:
            file.abspath = long_path_support(fspath(save_path / mapped_file))
        file.relpath = None
        yield file


def pieces_field(pieces: Iterable[bytes]) -> bytes:
    return b"".join(sha1(piece).digest() for piece in pieces)  # nosec


def create_torrent_info_dict(
    path: Path, piece_size: int, private: Optional[int] = None, sort: str = "name"
) -> Dict[str, Any]:
    """Create torrent info dict.

    path: Input file or directory
    piece_size: piece size, usually a power of two
    private: set private flag
    sort: sort by file path (name), file size (size) or use abitrary file system order (unordered)
    """

    if private is not None:
        assert_choice("private", private, {0, 1})

    assert_choice("sort", sort, {"name", "size", "unordered"})

    if piece_size < 1:
        raise ValueError("piece_size must be >= 1")

    if path.is_file():
        ret = {
            "name": path.name,
            "length": path.stat().st_size,
            "piece length": piece_size,
            "pieces": pieces_field(blockfileiter(path, chunk_size=piece_size)),
        }

    elif path.is_dir():
        files = list(p for p in path.rglob("*") if p.is_file())

        if sort == "name":
            files = sorted(files, key=lambda path: path.parts)
        elif sort == "size":
            files = sorted(files, key=lambda path: path.stat().st_size)

        assert files, "not implemented yet"

        ret = {
            "files": [
                {
                    "length": file.stat().st_size,
                    "path": file.relative_to(path).parts,
                }
                for file in files
            ],
            "name": path.name,
            "piece length": piece_size,
            "pieces": pieces_field(blockfilesiter(files, chunk_size=piece_size)),
        }

    else:
        raise ValueError("path neither file nor directory")

    if private is not None:
        ret["private"] = private

    return ret


def torrent_info_hash(d: dict) -> str:
    return sha1(BENCODE_BINARY.encode(d)).hexdigest()  # nosec


def get_torrent_hash(path: Path) -> str:
    return torrent_info_hash(read_torrent_info_dict(path))


def create_torrent(
    path: Path, piece_size: int, announce: str = "", private: Optional[bool] = None, sort: str = "name"
) -> bytes:
    info = create_torrent_info_dict(path, piece_size, private, sort)
    torrent = {"announce": announce, "info": info}

    return BENCODE_BINARY.encode(torrent)


def scrape(tracker_url: str, hashes: List[str], timeout: Optional[float] = 120.0) -> Dict[str, dict]:
    if not tracker_url.startswith(("http://", "https://")):
        raise ValueError(f"Only http(s) scrape is supported: <{tracker_url}>")

    base, announce = tracker_url.rsplit("/", 1)
    if "announce" not in announce:
        raise ValueError(f"Scrape not supported for {tracker_url}")

    scrape = announce.replace("announce", "scrape")
    scrape_url = f"{base}/{scrape}"

    hashes = [binascii.a2b_hex(hash) for hash in hashes]

    dec = bencodepy.BencodeDecoder(encoding="utf-8", encoding_fallback="all")

    r = requests.get(scrape_url, params={"info_hash": hashes}, timeout=timeout)
    r.raise_for_status()
    data = r.content
    try:
        tmp = dec.decode(data)
    except bencodepy.BencodeDecodeError:
        tmp = data.rstrip(b"\n")
        try:
            tmp = gzip.decompress(tmp)
        except gzip.BadGzipFile:
            raise ParseError("Failed to parse scrape response", data=data)
        tmp = dec.decode(tmp)

    try:
        files = tmp["files"]
    except KeyError:
        raise ParseError("Missing `files` key in scrape response", data=tmp)

    if len(files) < len(hashes):
        logger.warning("Less hashes returned (%s) than requested (%s)", len(files), len(hashes))

    return {k.hex(): v for k, v in files.items()}


if __name__ == "__main__":
    from argparse import ArgumentParser
    from pprint import pprint

    from genutility.object import compress as _compress

    DEFAULT_ANNOUNCE = "udp://tracker.opentrackr.org:1337/announce"
    DEFAULT_PIECE_LENGTH = 16 * 1024
    DEFAULT_SORT = "name"

    parser = ArgumentParser()
    parser.add_argument("action", choices=("read", "create"))
    parser.add_argument("--in-path", type=Path)
    parser.add_argument("--out-path", type=Path)
    parser.add_argument("--piece-size", type=int, default=DEFAULT_PIECE_LENGTH)
    parser.add_argument("--announce", default=DEFAULT_ANNOUNCE)
    parser.add_argument("--sort", default=DEFAULT_SORT, choices=("name", "size", "unordered"))
    args = parser.parse_args()

    if args.action == "read":
        if args.in_path.suffix == ".torrent":
            path_torrent = args.in_path
            path_fastresume = args.in_path.with_suffix(".fastresume")
        elif args.in_path.suffix == ".fastresume":
            path_torrent = args.in_path.with_suffix(".torrent")
            path_fastresume = args.in_path
        else:
            parser.error("Invalid file extension")

        d = read_torrent(path_torrent, binary=True)
        del d[b"info"][b"pieces"]
        pprint(_compress(d), width=120)
        print()
        d = read_torrent(path_fastresume, binary=False)
        d.pop("pieces", None)
        d.pop("piece_priority", None)
        d.pop("peers", None)
        pprint(_compress(d), width=120)
        print()
        pprint(list(iter_fastresume(path_fastresume)), width=120)

    elif args.action == "create":
        if not args.out_path:
            parser.error("--out-path required for action=create")

        data = create_torrent(args.in_path, args.piece_size, args.announce, sort=args.sort)
        with args.out_path.open("wb") as fw:
            fw.write(data)
