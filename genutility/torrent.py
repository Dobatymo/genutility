from __future__ import generator_stop

import logging
from hashlib import sha1
from itertools import compress, repeat, zip_longest
from os import fspath
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, Optional, Union

import bencode

from .exceptions import assert_choice
from .file import blockfileiter, blockfilesiter
from .filesystem import FileProperties
from .os import uncabspath

logger = logging.getLogger(__name__)


def read_torrent(path: str) -> dict:

    return bencode.bread(path)


def write_torrent(data: dict, path: str) -> None:

    bencode.bwrite(data, path)


def read_torrent_info_dict(path: str) -> dict:

    return bencode.bread(path)["info"]


def iterdecode(items: Iterable[Union[str, bytes]], encoding="latin1") -> Iterator[str]:
    for item in items:
        if isinstance(item, str):
            yield item
        elif isinstance(item, bytes):
            yield item.decode(encoding)
        else:
            raise TypeError


def iter_torrent(path: str) -> Iterator[FileProperties]:

    """Returns file informations from a torrent file.
    Hash (SHA-1) is obtained according to BEP0047 (if available).
    """

    """ *.utf-8 are hacks used by some clients to add utf-8 encoded strings.
        Now every string should be utf-8 encoded anyway, but in ancient times the encoding was not specified.
    """

    info = read_torrent_info_dict(path)

    if isinstance(info["name"], bytes):

        try:
            info["name"] = info["name"].decode("utf-8")
            assert False
        except UnicodeDecodeError:
            pass

        try:
            info["name"] = info["name.utf-8"]
            logger.warning("Non-standard `name.utf-8` key in torrent file: %s", path)
            assert isinstance(info["name"], str)
        except KeyError:
            info["name"] = info["name"].decode("latin1")
            logger.warning("info/name value uses invalid encoding in torrent file: %s", path)

    try:
        files = info["files"]
    except KeyError:
        yield FileProperties(info["name"], info["length"], False, hash=info.get("sha1"))
    else:
        for fd in files:
            try:
                path = "/".join(fd["path"])
            except TypeError:
                try:
                    path = "/".join(fd["path.utf-8"])
                except KeyError:
                    path = "/".join(iterdecode(fd["path"]))

            yield FileProperties(info["name"] + "/" + path, fd["length"], False, hash=fd.get("sha1"))


def iter_fastresume(path: str) -> Iterator[FileProperties]:
    """Files management in libtorrent fastresume files works like this (I think):
    - mapped_files contains a list with new files names, the list is truncated if the tail does not contain renamed files.
    - file_priority contains priorities for each file. Priority 0 means not downloaded.
    """

    path_torrent = fspath(Path(path).with_suffix(".torrent"))

    try:
        d = bencode.bread(path)
    except bencode.BencodeDecodeError as e:
        logger.warning("%s: %s", path, e)
        raise

    save_path = Path(d["qBt-savePath"])
    save_path_ = Path(d["save_path"])

    assert save_path == save_path_, f"{save_path}, {save_path_}"

    try:
        file_priority = d["file_priority"]
    except KeyError:
        file_priority = repeat(1)

    try:
        files = list(iter_torrent(path_torrent))
    except bencode.BencodeDecodeError as e:
        logger.warning("%s: %s", path_torrent, e)
        raise

    mapped_files = d.get("mapped_files", [])
    assert len(mapped_files) <= len(files)

    it = compress(zip_longest(files, mapped_files), file_priority)
    for file, mapped_file in it:
        if mapped_file is None:
            file.abspath = uncabspath(fspath(save_path / file.relpath))
        else:
            file.abspath = uncabspath(fspath(save_path / mapped_file))
        file.relpath = None
        yield file


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
