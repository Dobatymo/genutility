from __future__ import generator_stop

import errno
import logging
import os
import os.path
import platform
import re
import shutil
import stat
from datetime import datetime
from fnmatch import fnmatch
from functools import partial
from itertools import zip_longest
from operator import attrgetter
from os import DirEntry, PathLike, fspath
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, List, Optional, Set, Tuple, Union

from ._files import BaseDirEntry, MyDirEntryT, entrysuffix, to_dos_device_path
from .datetime import datetime_from_utc_timestamp
from .file import FILE_IO_BUFFER_SIZE, equal_files, iterfilelike
from .iter import is_empty
from .ops import logical_implication
from .os import _not_available, islink

PathType = Union[str, PathLike]
EntryType = Union[Path, DirEntry]

logger = logging.getLogger(__name__)

ascii_control = {chr(i) for i in range(1, 32)}
ntfs_illegal_chars = {"\0", "/"}
fat_illegal_chars = {"\0", "/", "?", "<", ">", "\\", ":", "*", "|", '"', "^"}  # ^ really?

windows_ntfs_illegal_chars = ntfs_illegal_chars | {"\\", ":", "*", "?", '"', "<", ">", "|"} | ascii_control
windows_fat_illegal_chars = fat_illegal_chars

windows_illegal_chars = windows_ntfs_illegal_chars | windows_fat_illegal_chars
unix_illegal_chars = {"\0", "/"}
mac_illegal_chars = {"\0", "/", ":"}

windows_sep = r"\/"
linux_sep = r"/"
mac_sep = r"/:"

windows_reserved_names = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "COM1",
    "COM2",
    "COM3",
    "COM4",
    "COM5",
    "COM6",
    "COM7",
    "COM8",
    "COM9",
    "LPT1",
    "LPT2",
    "LPT3",
    "LPT4",
    "LPT5",
    "LPT6",
    "LPT7",
    "LPT8",
    "LPT9",
}


class fileextensions:
    audio = ("wav", "mp3", "aac", "flac", "m4a", "m4b", "aiff", "ogg", "wma", "mka", "ac3", "dts")
    video = (
        "avi",
        "mp4",
        "m4v",
        "mkv",
        "mpg",
        "mpeg",
        "wmv",
        "mov",
        "flv",
        "f4v",
        "webm",
        "vob",
        "ogv",
        "m2ts",
        "rm",
        "rmvb",
        "asf",
        "3gp",
        "nsv",
        "divx",
        "ogm",
    )
    images = ("bmp", "jpg", "jpeg", "png", "gif", "tif", "tiff", "tga")

    archives = ("zip", "rar", "ace", "tar", "tgz", "tbz", "7z", "cab", "dmg", "wim")
    bytecode = ("pyc", "class")
    configuration = ("ini", "toml", "conf", "reg")
    database = ("cat", "sqlite", "db")
    documents = ("txt", "pdf", "doc", "docx", "ps", "rtf", "pgs")
    executables = ("exe", "dll", "so", "scr", "msi", "pyd", "sys", "cpl")  # native code
    image_archives = ("cbz", "cbr", "cb7", "cbt", "cba")
    scripts = ("bat", "ps1", "sh", "c", "cpp", "cs", "py", "php", "js", "lua", "pl")  # and source code files

    disc_images_binary = ("iso", "bin", "mdf", "img")
    disc_images_sidecar = ("cue", "mds", "ccd")
    disc_images = disc_images_binary + disc_images_sidecar

    game_images = ("gcn", "nds", "3ds", "wad", "xbx", "gba", "gb", "nes", "sfc", "n64", "z64")
    compressed = ("gz", "bz2", "lzma", "xz", "z")
    subtitles = ("srt", "sub", "idx", "sup", "ssa", "ass")
    scene = ("nfo", "sfv")

    windows = ("library-ms", "desklink", "lnk", "dmp")
    macos = ("crash",)
    os = windows + macos


class IllegalFilename(ValueError):
    pass


class WindowsIllegalFilename(IllegalFilename):
    pass


class FileProperties:

    __slots__ = ("relpath", "size", "isdir", "abspath", "id", "modtime", "hash")

    def __init__(
        self,
        relpath: Optional[str] = None,
        size: Optional[int] = None,
        isdir: Optional[bool] = None,
        abspath: Optional[str] = None,
        id: Optional[Any] = None,
        modtime: Optional[datetime] = None,
        hash: Optional[str] = None,
    ) -> None:

        if relpath is None and abspath is None:
            raise ValueError("Either `relpath` or `abspath` (or both) must be given")

        self.relpath = relpath
        self.size = size
        self.isdir = isdir
        self.abspath = abspath
        self.id = id
        self.modtime = modtime
        self.hash = hash

    @classmethod
    def keys(cls) -> Tuple[str, ...]:
        return cls.__slots__

    def values(self):
        return attrgetter(*self.__slots__)(self)

    def __iter__(self) -> tuple:

        return iter(self.values())

    def __eq__(self, other: Any) -> bool:

        return self.values() == other.values()

    def __repr__(self) -> str:

        args = (f"{k}={v!r}" for k, v in zip(self.keys(), self.values()) if v is not None)
        return "FileProperties({})".format(", ".join(args))


class DirEntryStub:
    __slots__ = ("name", "path")

    def __init__(self, name: str, path: str) -> None:
        self.name = name
        self.path = path


class MyDirEntry(BaseDirEntry):
    __slots__ = ("basepath", "_relpath", "follow")

    def __init__(self, entry):
        BaseDirEntry.__init__(self, entry)

        self.basepath: Optional[str] = None
        self._relpath: Optional[str] = None
        self.follow = True

    @property
    def relpath(self) -> str:

        if self._relpath is not None:
            return self._relpath

        if self.basepath is None:
            raise RuntimeError("relpath cannot be returned, because basepath is not set")

        self._relpath = os.path.relpath(self.entry.path, self.basepath)
        return self._relpath

    @relpath.setter
    def relpath(self, path: str) -> None:

        self._relpath = path


if platform.system() == "Windows":

    def long_path_support(path: str) -> str:
        return to_dos_device_path(os.path.abspath(path))

else:

    def long_path_support(path: str) -> str:
        return path


def mdatetime(path: PathType, aslocal: bool = False) -> datetime:

    """Returns the last modified date of `path`
    as a timezone aware datetime object.

    If `aslocal=True` it will be formatted as local time,
    and UTC otherwise (the default).
    """

    if isinstance(path, (Path, DirEntry)):
        mtime = path.stat().st_mtime
    else:
        mtime = os.stat(path).st_mtime

    return datetime_from_utc_timestamp(mtime, aslocal)


def rename(old: PathType, new: PathType) -> None:

    """Renames `old` to `new`. Fails if `new` already exists.
    This is the default behaviour of `os.rename` on Windows.
    This function should do the same cross-platform.
    It is however not race free.
    """

    # fixme: renaming a non-existing file in a non-existing folder yields a PermissionError not FileNotFoundError

    if os.path.exists(new):
        raise FileExistsError(new)

    os.renames(old, new)  # fixme: don't use rename*s*


def copy_file_generator(
    source: PathType, dest: PathType, buffer_size: int = FILE_IO_BUFFER_SIZE, overwrite_readonly: bool = False
) -> Iterator[None]:

    """Partial file is not deleted if exception gets raised anywhere."""

    try:
        os.makedirs(os.path.dirname(dest))
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

    if overwrite_readonly:
        try:
            make_writeable(dest)
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise

    with open(source, "rb") as src, open(dest, "wb") as dst:
        for data in iterfilelike(src, chunk_size=buffer_size):
            dst.write(data)
            yield

    shutil.copystat(source, dest)


def st_mode_to_str(st_mode: int) -> str:

    if stat.S_ISDIR(st_mode):
        return "directory"
    elif stat.S_ISREG(st_mode):
        return "regular file"
    elif stat.S_ISCHR(st_mode):
        return "character special device file"
    elif stat.S_ISBLK(st_mode):
        return "block special device file"
    elif stat.S_ISFIFO(st_mode):
        return "named pipe"
    elif stat.S_ISLNK(st_mode):
        return "symbolic link"
    elif stat.S_ISSOCK(st_mode):
        return "socket"
    else:
        return "unknown"


def append_to_filename(path: PathType, s: str) -> str:

    """Add `s` to the filename given in `path`. It's added before the extension, not after."""

    root, ext = os.path.splitext(path)
    return root + s + ext


def scandir_error_log(entry: DirEntry, exception) -> None:
    logger.exception("Error in %s", entry.path, exc_info=exception)


def scandir_error_log_warning(entry: DirEntry, exception) -> None:
    logger.warning("Error in %s", entry.path, exc_info=exception)


def scandir_error_raise(entry: DirEntry, exception) -> None:
    raise exception


def scandir_error_ignore(entry: DirEntry, exception) -> None:
    pass


def _scandir_rec_skippable(
    rootentry: DirEntry,
    files: bool = True,
    others: bool = False,
    follow_symlinks: bool = True,
    errorfunc: Callable[[DirEntry, Exception], None] = scandir_error_raise,
) -> Iterator[MyDirEntry]:

    try:
        with os.scandir(rootentry.path) as it:
            for entry in it:
                if files and entry.is_file(follow_symlinks=follow_symlinks):
                    yield MyDirEntry(entry)
                elif entry.is_dir(follow_symlinks=follow_symlinks):
                    if not follow_symlinks and islink(entry):  # must be a windows junction
                        continue
                    se = MyDirEntry(entry)
                    yield se
                    if se.follow:
                        for e in _scandir_rec_skippable(entry, files, others, follow_symlinks, errorfunc):
                            yield e
                else:
                    if others:
                        yield MyDirEntry(entry)
    except OSError as e:
        errorfunc(rootentry, e)


def _scandir_rec(
    rootentry: DirEntry,
    files: bool = True,
    dirs: bool = False,
    others: bool = False,
    rec: bool = True,
    follow_symlinks: bool = True,
    errorfunc: Callable[[DirEntry, Exception], None] = scandir_error_raise,
) -> Iterator[DirEntry]:

    try:
        with os.scandir(rootentry.path) as it:
            for entry in it:
                if files and entry.is_file(follow_symlinks=follow_symlinks):
                    yield entry
                elif entry.is_dir(follow_symlinks=follow_symlinks):
                    if not follow_symlinks and islink(
                        entry
                    ):  # must be a windows junction. entry.is_symlink() doesn't support junctions
                        continue
                    if dirs:
                        yield entry
                    if rec:
                        for e in _scandir_rec(entry, files, dirs, others, rec, follow_symlinks, errorfunc):
                            yield e
                else:
                    if others:
                        yield entry
    except OSError as e:
        errorfunc(rootentry, e)


def scandir_rec(
    path: PathType,
    files: bool = True,
    dirs: bool = False,
    others: bool = False,
    rec: bool = True,
    follow_symlinks: bool = True,
    relative: bool = False,
    allow_skip: bool = False,
    errorfunc: Callable[[MyDirEntryT, Exception], None] = scandir_error_log,
) -> Iterator[MyDirEntryT]:

    if not logical_implication(allow_skip, dirs and rec):
        raise ValueError("allow_skip implies dirs and rec")

    if isinstance(path, PathLike):
        path = fspath(path)

    entry = DirEntryStub(
        os.path.basename(path), long_path_support(path)
    )  # for python 2 compat. and long filename support

    if not allow_skip:
        it = _scandir_rec(entry, files, dirs, others, rec, follow_symlinks, errorfunc)
    else:
        it = _scandir_rec_skippable(entry, files, others, follow_symlinks, errorfunc)

    if not relative:
        return it
    else:
        basepath = long_path_support(path)
        if not allow_skip:
            # entry is a `os.DirEntry`
            def modpathrelative(entry):
                entry = MyDirEntry(entry)
                entry.basepath = basepath
                return entry

        else:
            # entry is a `MyDirEntry`
            def modpathrelative(entry):
                entry.basepath = basepath
                return entry

        return map(modpathrelative, it)


def scandir_rec_simple(
    path: str,
    files: bool = True,
    dirs: bool = False,
    others: bool = False,
    rec: bool = True,
    follow_symlinks: bool = True,
    errorfunc: Callable[[MyDirEntryT, Exception], None] = scandir_error_log_warning,
) -> Iterator[DirEntry]:

    entry = DirEntryStub(os.path.basename(path), path)
    return _scandir_rec(entry, files, dirs, others, rec, follow_symlinks, errorfunc)


def scandir_ext(
    path: PathType,
    extensions: Set[str],
    rec: bool = True,
    follow_symlinks: bool = False,
    relative: bool = False,
    errorfunc: Callable = scandir_error_log,
) -> Iterator[DirEntry]:

    for entry in scandir_rec(
        path, files=True, dirs=False, rec=rec, follow_symlinks=follow_symlinks, relative=relative, errorfunc=errorfunc
    ):
        if entrysuffix(entry).lower() in extensions:
            yield entry


# fixme: benchmark and delete
def scandir_ext_2(path: str, extensions: Set[str], rec: bool = True) -> Iterator[Path]:

    if rec:
        paths = Path(long_path_support(path)).rglob("*")
    else:
        paths = Path(long_path_support(path)).glob("*")

    for p in paths:
        if p.suffix.lower() in extensions:
            yield p


def _scandir_depth(rootentry: DirEntry, depth: int, errorfunc: Callable):

    try:
        with os.scandir(rootentry.path) as it:
            for entry in it:
                if entry.is_dir():
                    yield depth, entry
                    yield from _scandir_depth(entry, depth + 1, errorfunc)

        with os.scandir(rootentry.path) as it:
            for entry in it:
                if entry.is_file():
                    yield depth, entry

    except OSError as e:
        errorfunc(rootentry, e)


def scandir_depth(path: str, depth: int = 0, onerror: Callable = scandir_error_log) -> Iterator[Tuple[int, DirEntry]]:

    """Recursive version of `scandir` which yields the current path depth
    along with the DirEntry.
    Directories are returned first, then files.
    The order is arbitrary otherwise.
    """

    entry = DirEntryStub(
        os.path.basename(path), long_path_support(path)
    )  # for python 2 compat. and long filename support
    return _scandir_depth(entry, depth, onerror)


def make_readonly(path: PathType, stats: Optional[os.stat_result] = None) -> None:

    """deletes all write flags"""
    if not stats:
        stats = os.stat(path)
    os.chmod(path, stat.S_IMODE(stats.st_mode) & ~stat.S_IWUSR & ~stat.S_IWGRP & ~stat.S_IWOTH)


def make_writeable(path: PathType, stats: Optional[os.stat_result] = None) -> None:

    """set owner write flag"""
    if not stats:
        stats = os.stat(path)
    os.chmod(path, stat.S_IMODE(stats.st_mode) | stat.S_IWRITE)


def is_writeable(stats: os.stat_result) -> bool:

    return stats.st_mode & stat.S_IWRITE != 0


def is_readable(stats: os.stat_result) -> bool:

    return stats.st_mode & stat.S_IREAD != 0


def isfile(stats: os.stat_result) -> bool:

    return stat.S_ISREG(stats.st_mode)


def isdir(stats: os.stat_result) -> bool:

    return stat.S_ISDIR(stats.st_mode)


# was: islink
def statsislink(stats: os.stat_result) -> bool:

    return stat.S_ISLNK(stats.st_mode)


def extract_basic_stat_info(stats: os.stat_result) -> Tuple[int, int, int, int]:

    """Returns size, modification, creation time and access mode."""
    return (stats.st_size, stats.st_mtime, stats.st_ctime, stats.st_mode)


def safe_filename(filename: str, replacement: str = "") -> str:

    WIN = windows_illegal_chars
    UNIX = unix_illegal_chars
    MAC = mac_illegal_chars
    bad = set.union(WIN, UNIX, MAC)

    safe_filename_translation_table = str.maketrans({c: replacement for c in bad})

    return filename.translate(safe_filename_translation_table)  # fixme: return callable which accepts only filename


safe_filename_simple = safe_filename


def _char_subber(s: str, illegal_chars: Set[str], replacement: str) -> str:

    if set(replacement) & illegal_chars:
        raise ValueError("replace character cannot be a illegal character")

    regex = "[" + re.escape("".join(illegal_chars)) + "]"
    return re.sub(regex, replacement, s)


def _char_splitter(s: str, chars: Iterable[str]) -> List[str]:

    regex = "[" + re.escape("".join(chars)) + "]"
    return re.split(regex, s)


def _special_subber(s: str, replacement: str = "_") -> str:

    if s == "." or s == "..":
        return s.replace(".", replacement)

    return s


def windows_compliant_filename(filename: str, replacement: str = "_") -> str:
    """https://msdn.microsoft.com/en-us/library/aa365247.aspx"""
    # reg. wikipedia: \x7f is valid!
    # trailing dots and spaces are ignored by windows

    ret = _char_subber(filename, windows_illegal_chars, replacement).rstrip(". ")  # strip or replace?, translate

    root, _ = os.path.splitext(ret)

    if root.upper() in windows_reserved_names:
        raise WindowsIllegalFilename("filename would result in reserved name")

    return ret


def windows_compliant_dirname(filename: str, replacement: str) -> str:
    """https://msdn.microsoft.com/en-us/library/aa365247.aspx"""
    # reg. wikipedia: \x7f is valid!
    # trailing dots and spaces are ignored by windows

    ret = _char_subber(filename, windows_illegal_chars, replacement).rstrip(" ")

    root, _ = os.path.splitext(ret)

    if root.upper() in windows_reserved_names:
        raise WindowsIllegalFilename("filename would result in reserved name")

    return ret


def linux_compliant_filename(filename: str, replacement: str = "_") -> str:

    filename = _special_subber(filename, replacement)
    return _char_subber(filename, unix_illegal_chars, replacement)


def linux_compliant_dirname(filename: str, replacement: str = "_") -> str:

    return _char_subber(filename, unix_illegal_chars, replacement)


def mac_compliant_filename(filename: str, replacement: str = "_") -> str:

    filename = _special_subber(filename, replacement)
    return _char_subber(filename, mac_illegal_chars, replacement)


def mac_compliant_dirname(filename: str, replacement: str = "_") -> str:

    return _char_subber(filename, mac_illegal_chars, replacement)


def windows_split_path(s: str) -> List[str]:

    return _char_splitter(s, windows_sep)


def linux_split_path(s: str) -> List[str]:

    return _char_splitter(s, linux_sep)


def mac_split_path(s: str) -> List[str]:

    return _char_splitter(s, mac_sep)


system = platform.system()

if system == "Windows":
    compliant_filename = windows_compliant_filename
    compliant_dirname = windows_compliant_dirname
    split_path = windows_split_path
elif system == "Linux":
    compliant_filename = linux_compliant_filename
    compliant_dirname = linux_compliant_dirname
    split_path = linux_split_path
elif system == "Darwin":
    compliant_filename = mac_compliant_filename
    compliant_dirname = mac_compliant_dirname
    split_path = mac_split_path
else:
    compliant_filename = _not_available("compliant_filename")
    compliant_dirname = _not_available("compliant_dirname")
    split_path = _not_available("split_path")


def compliant_path(path: str, replace: str = "_") -> str:

    fn_func = partial(compliant_dirname, replace=replace)
    path_compontents = split_path(path)

    ret = os.sep.join(map(fn_func, path_compontents[:-1]))
    ret = os.path.join(ret, compliant_filename(path_compontents[-1]))
    return ret


def reldirname(path: PathType) -> str:

    ret = os.path.dirname(path)
    if not ret:
        ret = "."

    return ret


def equal_dirs_iter(dir1: PathType, dir2: PathType, follow_symlinks: bool = False) -> Iterator[Tuple[str, str, str]]:

    """Tests if two directories are equal. Doesn't handle links."""

    def entry_path_size(entry):
        return entry.path, entry.stat().st_size

    files1 = sorted(map(entry_path_size, scandir_rec(dir1, follow_symlinks=follow_symlinks)))  # get rel paths
    files2 = sorted(map(entry_path_size, scandir_rec(dir2, follow_symlinks=follow_symlinks)))  # get rel paths

    for (path1, size1), (path2, size2) in zip_longest(files1, files2):
        if path1 != path2:
            yield ("name", path1, path2)

        elif size1 != size2:
            yield ("size", path1, path2)

    for (path1, size1), (path2, size2) in zip_longest(files1, files2):
        if path1 == path2 and size1 == size2 and not equal_files(path1, path2):
            yield ("data", path1, path2)


def equal_dirs(dir1: PathType, dir2: PathType) -> bool:
    return is_empty(equal_dirs_iter(dir1, dir2))


def realpath_win(path: PathType) -> str:

    """fix for os.path.realpath() which doesn't work under Win7"""

    path = os.path.abspath(path)
    if islink(path):
        return os.path.normpath(os.path.join(os.path.dirname(path), os.readlink(path)))
    else:
        return path


def search(
    directories: Iterable[PathType],
    pattern: str,
    dirs: bool = True,
    files: bool = True,
    rec: bool = True,
    follow_symlinks: bool = False,
) -> Iterator[DirEntry]:

    """Search for files and folders matching the wildcard `pattern`."""

    for directory in directories:
        for entry in scandir_rec(directory, dirs=dirs, files=files, rec=rec, follow_symlinks=follow_symlinks):
            if fnmatch(entry.name, pattern):
                yield entry


def rename_files_in_folder(
    path: PathType, pattern: str, transform: Callable, template: str, rec: bool = True, follow_symlinks: bool = False
) -> None:

    cpattern = re.compile(pattern)

    for entry in scandir_rec(path, files=True, dirs=False, rec=rec, follow_symlinks=follow_symlinks):
        filepath = entry.path
        base, name = os.path.split(filepath)

        m = cpattern.match(name)
        if not m:
            continue
        args = transform(*m.groups())

        to = template.format(*args)
        os.rename(filepath, os.path.join(base, to))


def clean_directory_by_extension(path: PathType, ext: str, rec: bool = True, follow_symlinks: bool = False) -> None:

    """Deletes all files of type `ext` if the same file without the ext exists
    and rename if it does not exit."""

    # delete .ext if normal file exists
    for entry in scandir_rec(path, files=True, dirs=False, rec=rec, follow_symlinks=follow_symlinks):
        filepath = entry.path
        if not filepath.endswith(ext):
            file_to_delete = filepath + ext
            if os.path.isfile(file_to_delete):
                logger.info("Remove: %s", file_to_delete)
                try:
                    os.remove(file_to_delete)
                except OSError:
                    logger.exception("Could not delete: %s", file_to_delete)
                    break

    # rename all .ext to normal
    for entry in scandir_rec(path, files=True, dirs=False, rec=rec, follow_symlinks=follow_symlinks):
        filepath = entry.path
        if entry.name.endswith(ext):
            target = filepath[: -len(ext)]
            try:
                logger.info("Rename: %s -> %s", filepath, target)
                os.rename(filepath, target)
            except OSError:
                logger.exception("Should not have happened")
                break


def iter_links(path: PathType) -> Iterator[str]:

    """Yields all directory symlinks (and junctions on windows)."""

    for dirpath, dirnames, filenames in os.walk(path):
        for dirname in dirnames:
            joined = os.path.join(dirpath, dirname)
            if islink(joined):
                yield joined


def normalize_seps(path: str) -> str:

    """Converts \\ to /"""

    return path.replace("\\", "/")


class Counts:
    __slots__ = ("dirs", "files", "others")

    def __init__(self) -> None:
        self.dirs = 0
        self.files = 0
        self.others = 0

    def __iadd__(self, other: "Counts") -> "Counts":

        self.dirs += other.dirs
        self.files += other.files
        self.others += other.others

        return self

    def null(self) -> bool:

        return self.dirs == 0 and self.files == 0 and self.others == 0


def _scandir_counts(
    rootentry: MyDirEntryT,
    files: bool = True,
    others: bool = True,
    rec: bool = True,
    total: bool = False,
    errorfunc: Callable = scandir_error_raise,
) -> Iterator[Tuple[DirEntry, Optional[Counts]]]:

    counts = Counts()

    try:
        with os.scandir(rootentry.path) as it:
            for entry in it:

                if entry.is_dir():
                    counts.dirs += 1
                    if rec:
                        for subentry, subcounts in _scandir_counts(entry, files, others, rec, total, errorfunc):
                            yield subentry, subcounts

                            if total:
                                assert subcounts
                                counts += subcounts

                elif entry.is_file():
                    counts.files += 1
                    if files:
                        yield entry, None

                else:
                    counts.others += 1
                    if others:
                        yield entry, None

        yield rootentry, counts  # yield after the loop

    except OSError as e:
        errorfunc(rootentry, e)


def scandir_counts(
    path: PathType,
    files: bool = True,
    others: bool = True,
    rec: bool = True,
    total: bool = False,
    onerror: Callable = scandir_error_log,
) -> Iterator[Tuple[DirEntry, Optional[Counts]]]:

    """A recursive variant of scandir() which also returns the number of files/directories
    within directories.
    If total is True, the numbers will be calculated recursively as well.
    """

    if isinstance(path, PathLike):
        path = fspath(path)

    entry = DirEntryStub(os.path.basename(path), long_path_support(path))
    return _scandir_counts(entry, files, others, rec, total, onerror)


def shutil_onerror_remove_readonly(func, path, exc_info):

    """onerror function for the `shutil.rmtree` function.
    Makes read-only files writable and tries again.
    """

    stats = os.stat(path)
    if is_readable(stats):
        make_writeable(path, stats)
        func(path)
    else:
        raise


def _rmtree(path: str, ignore_errors: bool = False, onerror: Optional[Callable[[Callable, str, Any], None]] = None):

    """Compared to `shutil.rmtree`, this removes files instantly,
    instead of collecting the whole directory contents first.
    """

    import sys
    from shutil import _rmtree_isdir

    if ignore_errors:

        def onerror(*args):
            pass

    elif onerror is None:

        def onerror(*args):
            raise

    try:
        with os.scandir(path) as scandir_it:
            for entry in scandir_it:
                fullname = entry.path
                if _rmtree_isdir(entry):
                    try:
                        if entry.is_symlink():
                            raise OSError("Cannot call _rmtree on a symbolic link")
                    except OSError:
                        onerror(os.path.islink, fullname, sys.exc_info())
                        continue
                    yield from _rmtree(fullname, onerror)
                else:
                    try:
                        os.unlink(fullname)
                        yield None
                    except OSError:
                        onerror(os.unlink, fullname, sys.exc_info())

    except OSError:
        onerror(os.scandir, path, sys.exc_info())

    try:
        os.rmdir(path)
        yield None
    except OSError:
        onerror(os.rmdir, path, sys.exc_info())
