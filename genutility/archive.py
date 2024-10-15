from os import PathLike, fspath, scandir
from typing import IO, Callable, Dict, Iterator, Optional, Tuple, Union

from ._files import PathType, entrysuffix
from .file import _check_arguments, _stripmode, copen, wrap_text


def iter_zip(
    file: Union[PathType, IO[bytes]],
    mode: str = "rb",
    encoding: Optional[str] = None,
    errors: Optional[str] = None,
    newline: Optional[str] = None,
    password: Optional[bytes] = None,
) -> Iterator[Tuple[str, IO]]:
    """
    Iterate file-pointers to archived files. They are valid for one iteration step each.
    If `file` is a file-like, it must be seekable. It is untested if unbuffered file-likes work.
    """

    # from pyzipper import AESZipFile as ZipFile
    from zipfile import ZipFile

    encoding = _check_arguments(mode, encoding)
    newmode = _stripmode(mode)

    with ZipFile(file, newmode) as zf:
        for zi in zf.infolist():
            if not zi.is_dir():
                with zf.open(zi, newmode, password) as bf:
                    yield zi.filename, wrap_text(bf, mode, encoding, errors, newline)


def iter_tar(
    file: Union[PathType, IO[bytes]],
    mode: str = "rb",
    encoding: Optional[str] = None,
    errors: Optional[str] = None,
    newline: Optional[str] = None,
) -> Iterator[Tuple[str, IO]]:
    """
    Iterate file-pointers to archived files. They are valid for one iteration step each.
    With the correct mode, `file` can be a non-seekable file-like. It is untested if unbuffered file-likes work.
    """

    import tarfile

    encoding = _check_arguments(mode, encoding)
    newmode = _stripmode(mode)

    if isinstance(file, PathLike):
        file = fspath(file)

    if isinstance(file, str):
        cls = tarfile.open(name=file, mode=newmode + "|*")
    else:
        cls = tarfile.open(fileobj=file, mode=newmode + "|*")

    with cls as tf:
        for ti in tf:
            if ti.isfile():  # fixme: what about links?
                bf = tf.extractfile(ti)
                assert bf, "member `ti` is file, but still `extractfile` returned `None`"
                with bf:  # no `mode` for `extractfile`
                    yield ti.name, wrap_text(bf, mode, encoding, errors, newline)


def iter_7zip(
    file: Union[PathType, IO[bytes]],
    mode: str = "rb",
    encoding: Optional[str] = None,
    errors: Optional[str] = None,
    newline: Optional[str] = None,
    password: Optional[str] = None,
) -> Iterator[Tuple[str, IO]]:
    """It is untested if unbuffered file-likes work."""

    from py7zr import SevenZipFile

    encoding = _check_arguments(mode, encoding)
    newmode = _stripmode(mode)

    with SevenZipFile(file, mode=newmode) as zf:
        for fname, bf in zf.readall().items():
            yield fname, wrap_text(bf, mode, encoding, errors, newline)


def iter_dir(
    path: PathType,
    mode: str = "rb",
    encoding: Optional[str] = None,
    errors: Optional[str] = None,
    newline: Optional[str] = None,
    follow_symlinks: bool = True,
    archives: bool = False,
    joiner: str = "/",
) -> Iterator[Tuple[str, IO]]:
    """
    Iterate file-pointers to files in directory `path`.
    They are valid for one iteration step each.
    If `archives` is True, archives like zip files will be traversed as well.
    """

    encoding = _check_arguments(mode, encoding)

    archive_funcs: Dict[
        str, Callable[[str, str, Optional[str], Optional[str], Optional[str]], Iterator[Tuple[str, IO]]]
    ] = {
        ".zip": iter_zip,
        ".tar": iter_tar,
        ".tgz": iter_tar,  # what about tar.gz
        ".tbz": iter_tar,  # what about tar.bz2
        ".7z": iter_7zip,
    }

    if archives:
        open = copen

    with scandir(path) as scan:
        for entry in scan:
            if entry.is_file(follow_symlinks=follow_symlinks):
                ext = entrysuffix(entry).lower()
                iter_archive = archive_funcs.get(ext, None)
                if archives and iter_archive:
                    for name, fr in iter_archive(entry.path, mode, encoding, errors, newline):
                        yield entry.path + joiner + name, fr
                else:
                    with open(entry.path, mode, encoding=encoding, errors=errors, newline=newline) as fr:
                        yield entry.path, fr

            elif entry.is_dir(follow_symlinks=follow_symlinks):
                yield from iter_dir(entry.path, mode, encoding, errors, newline, follow_symlinks, archives)
