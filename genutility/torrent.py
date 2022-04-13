from __future__ import generator_stop

from hashlib import sha1
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, Optional

import bencode

from .exceptions import assert_choice
from .file import blockfileiter, blockfilesiter
from .filesystem import FileProperties


def read_torrent(path: str) -> dict:

    return bencode.bread(path)


def write_torrent(data: dict, path: str) -> None:

    bencode.bwrite(data, path)


def read_torrent_info_dict(path: str) -> dict:

    return bencode.bread(path)["info"]


def iter_torrent(path: str) -> Iterator[FileProperties]:

    """Returns file informations from a torrent file.
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


def pieces_field(pieces: Iterable[bytes]) -> bytes:
    return b"".join(sha1(piece).digest() for piece in pieces)  # nosec


def create_torrent_info_dict(path: Path, piece_size: int, private: Optional[int] = None) -> Dict[str, Any]:

    if private is not None:
        assert_choice("private", private, {0, 1})

    if path.is_file():
        ret = {
            "name": path.name,
            "length": path.stat().st_size,
            "piece length": piece_size,
            "pieces": pieces_field(blockfileiter(path, chunk_size=piece_size)),
        }

    elif path.is_dir():
        files = []  # fixme: not implemented yet

        assert files, "not implemented yet"

        ret = {
            "name": path.name,
            "files": [
                {
                    "length": length,
                    "path": path.parts,
                }
                for length, path in files
            ],
            "piece length": piece_size,
            "pieces": pieces_field(blockfilesiter((p for _, p in files), chunk_size=piece_size)),
        }

    else:
        raise ValueError("path neither file nor directory")

    if private is not None:
        ret["private"] = private

    return ret


def torrent_info_hash(d: dict) -> str:
    return sha1(bencode.bencode(d)).hexdigest()  # nosec


def get_torrent_hash(path: str) -> str:
    return torrent_info_hash(read_torrent_info_dict(path))


def create_torrent(path: Path, piece_size: int, announce: str = "") -> bytes:

    info = create_torrent_info_dict(path, piece_size)
    torrent = {"info": info, "announce": announce}

    return bencode.bencode(torrent)
