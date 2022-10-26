from __future__ import generator_stop

import os.path
from io import SEEK_END, SEEK_SET, BufferedIOBase, RawIOBase, TextIOBase, TextIOWrapper
from mmap import mmap
from os import PathLike, fdopen, fspath, scandir
from sys import stdout
from typing import IO, BinaryIO, Callable, Dict, Iterable, Iterator, Optional, TextIO, Tuple, TypeVar, Union, overload

from ._files import PathType, entrysuffix
from .iter import consume, iter_equal, resizer
from .math import PosInfInt
from .ops import logical_implication, logical_xor

Data = TypeVar("Data", str, bytes)

FILE_IO_BUFFER_SIZE = 8 * 1024 * 1024


class Empty(OSError):
    pass


def _check_arguments(mode: str, encoding: Optional[str] = None) -> Optional[str]:

    is_text = "t" in mode
    is_binary = "b" in mode

    if not logical_xor(is_text, is_binary):
        raise ValueError(f"Explicit text or binary mode required: {mode}")

    if not logical_implication(is_binary, encoding is None):
        raise ValueError("Encoding is not None for binary file")

    if is_text:
        encoding = encoding or "utf-8"

    return encoding


def _stripmode(mode: str) -> str:
    return "".join(set(mode) - {"t", "b"})


def read_file(
    path: PathType, mode: str = "b", encoding: Optional[str] = None, errors: Optional[str] = None
) -> Union[str, bytes]:

    """Reads and returns whole file. If content is not needed use consume_file()"""

    encoding = _check_arguments(mode, encoding)

    if "r" not in mode:
        mode = "r" + mode

    with open(path, mode, encoding=encoding, errors=errors) as fr:
        return fr.read()


def write_file(
    data: Union[str, bytes],
    path: PathType,
    mode: str = "wb",
    encoding: Optional[str] = None,
    errors: Optional[str] = None,
) -> None:

    """Writes file."""

    encoding = _check_arguments(mode, encoding)

    with open(path, mode, encoding=encoding, errors=errors) as fw:
        fw.write(data)


@overload
def read_or_raise(fin: IO[Data], size: int) -> Data:

    ...


@overload
def read_or_raise(fin: mmap, size: int) -> bytes:

    ...


def read_or_raise(fin, size):

    """Instead of returning a result smaller than `size` like `io.read()`,
    it raises and EOFError.
    """

    data = fin.read(size)
    if len(data) == 0:  # fixme: add `and size != 0`?
        raise Empty
    elif len(data) != size:
        raise EOFError

    return data


def get_file_range(path: PathType, start: int, size: int) -> bytes:

    with open(path, "rb") as fp:
        fp.seek(start)
        return fp.read(size)


def truncate_file(path: PathType, size: int) -> None:

    with open(path, "r+b") as fp:
        fp.truncate(size)


def wrap_text(bf, mode, encoding, errors, newline):
    if "t" in mode:
        tf = TextIOWrapper(bf, encoding, errors, newline)
        tf.mode = mode
        return tf
    return bf


def copen(
    file: Union[PathType, IO, int],
    mode: str = "rt",
    archive_file: Optional[str] = None,
    encoding: Optional[str] = None,
    errors: Optional[str] = None,
    newline: Optional[str] = None,
    compresslevel: int = 9,
    ext: Optional[str] = None,
    handle_archives: bool = True,
) -> IO:

    """Generic file open method. It supports transparent compression and improved text-mode handling.

    `file`: Can be a path, file-like or file descriptor.
    `mode`, `errors` and `newline`: see `io.open`
    `archive_file`: if a zip file is opened, this specifies the file within the archive.
    `encoding`: if `None` it defaults to "utf-8" in text-mode. It doesn't use any locale.
    `compresslevel`: 0-9, 0: no compression, 1: least, 9: highest compression.
            Only used if a compressed format is specified.
    `ext`: if `file` is a file-like object, than this can be one of {".gz", ".bz2", ".zip"}
            to enable transparent compression
    `handle_archives`: Allow transparent handling of archives. Defaults to `True`.
        If `archive_file` is not given for archives which require it, the archive file will be treated as a normal file.

    Returns a file-like object. If `file` was a fd,
            it will be closed when the file-like object is closed.
    """

    encoding = _check_arguments(mode, encoding)

    if archive_file is not None and handle_archives is False:
        raise ValueError("handle_archives must be True to allow archive_file to be used")

    if isinstance(file, (str, PathLike)):
        ext = os.path.splitext(file)[1].lower()
    elif isinstance(file, int):
        file = fdopen(file, mode, encoding=encoding, errors=errors, newline=newline)
        ext = ext and ext.lower()
    else:
        ext = ext and ext.lower()

    if handle_archives:
        if ext == ".gz":
            import gzip

            return gzip.open(file, mode, compresslevel=compresslevel, encoding=encoding, errors=errors, newline=newline)

        elif ext == ".bz2":
            import bz2

            return bz2.open(file, mode, compresslevel=compresslevel, encoding=encoding, errors=errors, newline=newline)

        elif ext == ".zip" and archive_file:

            from zipfile import ZipFile

            newmode = _stripmode(mode)

            with ZipFile(
                file, newmode
            ) as zf:  # note: even if the outer zip file is closed, the inner file can still be read apparently
                bf = zf.open(archive_file, newmode, force_zip64=True)

            return wrap_text(bf, mode, encoding, errors, newline)

    if isinstance(file, TextIOWrapper):
        return file

    if hasattr(file, "read") or hasattr(file, "write"):  # file should be in binary mode here
        return wrap_text(file, mode, encoding, errors, newline)

    return open(file, mode, encoding=encoding, errors=errors, newline=newline)


class OpenFileAndDeleteOnError:

    """Context manager which opens a file using the same arguments as `open`,
    but deletes the file in case an exception occurs after opening.
    """

    def __init__(
        self,
        file: PathType,
        mode: str = "rt",
        encoding: Optional[str] = None,
        errors: Optional[str] = None,
        newline: Optional[str] = None,
        compresslevel: int = 9,
    ) -> None:

        encoding = _check_arguments(mode, encoding)

        self.file = file
        self.mode = mode
        self.encoding = encoding
        self.errors = errors
        self.newline = newline
        self.compresslevel = compresslevel
        self.fp: Optional[IO] = None

    def __enter__(self) -> IO:

        self.fp = copen(self.file, self.mode, None, self.encoding, self.errors, self.newline, self.compresslevel)
        return self.fp

    def __exit__(self, exc_type, exc_value, traceback):
        self.fp.close()
        if exc_type:
            # fixme: race condition
            # use https://stackoverflow.com/a/3594593 and `ReOpenFile` on Windows
            # or SetFileInformationByHandle
            # see also: https://nullprogram.com/blog/2016/08/07/
            os.remove(self.file)


class OptionalWriteOnlyFile:
    def __init__(
        self,
        path: Optional[PathType] = None,
        mode: str = "xb",
        encoding: Optional[str] = None,
        errors: Optional[str] = None,
        newline: Optional[str] = None,
        compresslevel: int = 9,
    ) -> None:

        if path:
            self.fp: Optional[IO] = copen(
                path, mode, encoding=encoding, errors=errors, newline=newline, compresslevel=compresslevel
            )
        else:
            self.fp = None

    def __enter__(self):
        if self.fp:
            return self.fp
        else:
            return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.fp:
            self.fp.close()

    def write(self, data):
        pass

    def seek(self, offset, whence=None):
        pass


class StdoutFile:
    def __init__(
        self,
        path: Optional[PathType] = None,
        mode: str = "xb",
        encoding: Optional[str] = None,
        errors: Optional[str] = None,
        newline: Optional[str] = None,
        compresslevel: int = 9,
    ) -> None:

        encoding = _check_arguments(mode, encoding)

        if path:
            self.fp = copen(path, mode, encoding=encoding, errors=errors, newline=newline, compresslevel=compresslevel)
            self.doclose = True
        else:
            self.doclose = False
            if "b" in mode:
                self.fp = stdout.buffer
            elif "t" in mode:
                self.fp = stdout
            else:
                raise ValueError(f"Explicit text or binary mode required: {mode}")

    def __enter__(self):
        return self.fp

    def __exit__(self, exc_type, exc_value, traceback):
        if self.doclose:
            self.fp.close()


class PathOrBinaryIO:
    def __init__(self, fname: Union[PathType, BinaryIO], mode: str = "rb", close: bool = False) -> None:

        if isinstance(fname, (RawIOBase, BufferedIOBase)):
            self.doclose: bool = close
            self.fp: BinaryIO = fname
        else:
            self.doclose = True
            self.fp = copen(fname, mode)

    def __enter__(self) -> IO:

        return self.fp

    def __exit__(self, exc_type, exc_value, traceback):
        if self.doclose:
            self.fp.close()


class PathOrTextIO:
    def __init__(
        self,
        fname: Union[PathType, TextIO],
        mode: str = "rt",
        encoding: str = "utf-8",
        errors: str = "strict",
        newline: Optional[str] = None,
        close: bool = False,
    ) -> None:

        if isinstance(fname, TextIOBase):
            self.doclose: bool = close
            self.fp: TextIO = fname
        else:
            self.doclose = True
            self.fp = copen(fname, mode, encoding=encoding, errors=errors, newline=newline)

    def __enter__(self) -> IO:

        return self.fp

    def __exit__(self, exc_type, exc_value, traceback):
        if self.doclose:
            self.fp.close()


class LastLineFile:

    chunk_size = 1024 * 4
    nl = "\n"

    def __init__(self, path, mode="rt+"):
        self.f = open(path, mode)
        self.ll_pos = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        self.f.close()

    def _seek_to_last_line(self):
        if self.ll_pos is None:
            self.ll_pos = self._get_last_line_pos()

        self.f.seek(self.ll_pos, SEEK_SET)

    def _get_last_line_pos(self):
        self.f.seek(0, SEEK_END)
        pos = self.f.tell()
        ret_pos = 0
        while pos > 0:
            seek_next = max(pos - self.chunk_size, 0)
            self.f.seek(seek_next, SEEK_SET)
            chunk = self.f.read(pos - seek_next)
            fpos = chunk.rfind("\n")
            if fpos != -1:
                ret_pos = seek_next + fpos + 1
                if ret_pos != pos:
                    break
            pos = seek_next
        return ret_pos

    def _validate(self, s):
        if self.nl in s:
            raise ValueError("Newline in input")

    def read(self):
        self._seek_to_last_line()
        return self.f.read()

    def newline(self, s):
        self.f.seek(0, SEEK_END)
        ret = self.f.write(self.nl)
        self.ll_pos = self.f.tell()
        return ret

    def replace(self, s):
        self._validate(s)
        self._seek_to_last_line()
        ret = self.f.write(s)
        self.f.truncate()
        return ret


class Tell:
    def __init__(self, fp: IO) -> None:

        try:
            assert not fp.seekable()
        except AttributeError:
            pass

        self._fp = fp
        self._pos = 0

    # wrapped

    def read(
        self, size=None
    ):  # the docs for `io.BufferedIOBase` say that size=-1, but that's not true for `HTTPResponse`
        ret = self._fp.read(size)
        self._pos += len(ret)
        return ret

    def read1(self, n=-1):
        ret = self._fp.read1(n)
        self._pos += len(ret)
        return ret

    def readall(self):
        ret = self._fp.readall()
        self._pos += len(ret)
        return ret

    def readline(self, limit=-1):
        ret = self._fp.readline(limit)
        self._pos += len(ret)
        return ret

    def readlines(self, hint=-1):
        raise NotImplementedError
        return self._fp.readlines(hint)

    def readinto(self, b):
        ret = self._fp.readinto(b)
        self._pos += ret
        return ret

    def readinto1(self, b):
        ret = self._fp.readinto1(b)
        self._pos += ret
        return ret

    def write(self, b):  # fixme: should this be added to _pos?
        return self._fp.write(b)

    def writelines(self, lines):  # fixme: should this be added to _pos?
        return self._fp.writelines(lines)

    def seek(self, offset, whence=SEEK_SET):
        raise OSError("Stream is not seekable")

    def tell(self):
        return self._pos

    # redirected

    def close(self):
        return self._fp.close()

    def detach(self):
        return self._fp.detach()

    def fileno(self):
        return self._fp.fileno()

    def flush(self):
        return self._fp.flush()

    def isatty(self):
        return self._fp.isatty()

    def readable(self):
        return self._fp.readable()

    def seekable(self):
        return self._fp.seekable()

    def truncate(self, size=None):
        return self._fp.truncate(size)

    def writable(self):
        return self._fp.writable()


from collections import deque
from urllib import response


class BufferedTell(response.addinfourl):  # fixme: untested!!!
    def __init__(self, filesize):
        # response.addinfourl.__init__(self, *args, **kwargs)
        self._pos = 0
        self._read = 0
        self.filesize = filesize
        self.buf = deque(maxlen=1024)

    def read(self, num=-1):
        if num == -1:
            num = self.filesize - self._pos
            print("num=-1")
        if self._pos == self._read:
            self._pos += num
            self._read += num
            data = response.addinfourl.read(num)
            self.buf.extend(data)
            return data
        elif self._pos < self._read:
            delta = self._read - self._pos
            self._pos += num
            if num <= delta:
                data = b"".join(self.buf.pop() for i in range(delta))
                self.buf.extend(data[::-1])
                return data[-1 : -1 - num : -1]
            else:
                datab = b"".join(self.buf.pop() for i in range(delta))
                datab = datab[::-1]
                self.buf.extend(datab)
                dataf = response.addinfourl.read(num - delta)
                self.buf.extend(dataf)
                return datab + dataf
        else:
            # return b""
            raise Exception("Unbuffered read")

    def tell(self):
        return self._pos

    def seek(self, offset, whence=0):
        if whence == 0:
            self._pos = offset
        elif whence == 1:
            self._pos += offset
        elif whence == 2:
            self._pos = self.filesize - offset
        else:
            raise ValueError("Unknown whence")


def copyfilelike(
    fin: IO,
    fout: IO,
    amount: Optional[int] = None,
    buffer: int = FILE_IO_BUFFER_SIZE,
    report: Optional[Callable] = None,
) -> int:

    """Read data from `fin` in chunks of size `buffer` and write them to `fout`.
    Optionally limit the amount of data to `amount`. `report` can be a callable which receives
    the total number of bytes copied and bytes remaining.
    see `shutil.copyfileobj`
    """

    # todo: have different input and output buffers

    _amount = amount or PosInfInt

    copied = 0
    while _amount > 0:
        if report:
            report(copied, _amount + copied)

        data = fin.read(min(buffer, _amount))

        if not data:
            break
        fout.write(data)
        _amount -= len(data)
        copied += len(data)
    return copied


def simple_file_iter(fr: IO[Data], chunk_size: int = FILE_IO_BUFFER_SIZE) -> Iterator[Data]:

    """Iterate file-like object `fr` and yield chunks of size `chunk_size`."""

    assert isinstance(chunk_size, int), "chunk_size needs to be an integer"

    # return iter(partial(fr.read, chunk_size), "") sentinel cannot be defined well
    while True:
        data = fr.read(chunk_size)
        if data:
            yield data
        else:
            break


def reversed_file_iter(fp: IO[Data], chunk_size: int = FILE_IO_BUFFER_SIZE) -> Iterator[Data]:

    """Generate blocks of file's contents in reverse order."""

    fp.seek(0, SEEK_END)
    here = fp.tell()
    while here > 0:
        delta = min(chunk_size, here)
        here -= delta
        fp.seek(here, SEEK_SET)
        yield fp.read(delta)


def limited_file_iter(fr: IO[Data], amount: int, chunk_size: int = FILE_IO_BUFFER_SIZE) -> Iterator[Data]:

    """Iterate file-like object `fr` and yield chunks of size `chunk_size`.
    Limit output to `amount` bytes.
    """

    while amount > 0:
        data = fr.read(min(chunk_size, amount))
        if not data:
            break
        yield data
        amount -= len(data)


def iterfilelike(
    fr: IO[Data], start: int = 0, amount: Optional[int] = None, chunk_size: int = FILE_IO_BUFFER_SIZE
) -> Iterable[Data]:

    """Iterate file-like object `fr` and yield chunks of size `chunk_size`.
    Starts reading at `start` and optionally limit output to `amount` bytes.
    """

    if start:
        fr.seek(start)

    if amount is None:
        return simple_file_iter(fr, chunk_size)
    else:
        return limited_file_iter(fr, amount, chunk_size)


def blockfileiter(
    path: PathType,
    mode: str = "rb",
    encoding: Optional[str] = None,
    errors: Optional[str] = None,
    start: int = 0,
    amount: Optional[int] = None,
    chunk_size: int = FILE_IO_BUFFER_SIZE,
) -> Iterator[Union[str, bytes]]:

    """Iterate over file at `path` and yield chunks of size `chunk_size`.
    Optionally limit output to `amount` bytes.
    """

    encoding = _check_arguments(mode, encoding)

    with open(path, mode, encoding=encoding, errors=errors) as fr:
        yield from iterfilelike(fr, start, amount, chunk_size)


def blockfilesiter(paths: Iterable[PathType], chunk_size: int = FILE_IO_BUFFER_SIZE) -> Iterator[bytes]:

    """Iterate over a list of files and return their contents in a
    continuous stream of chunks of size `chunk_size`.
    That means one chunk can span multiple files.
    """

    chunk = b""

    for path in paths:
        with open(path, "rb") as fr:
            if len(chunk) != 0:
                # print("a")
                data = fr.read(chunk_size - len(chunk))
                chunk += data  # fixme: probably slow for lots of small files

            if len(chunk) == chunk_size:
                # print("b")
                yield chunk
                chunk = b""

            if len(chunk) == 0:
                # print("c")
                for data in iterfilelike(fr, chunk_size=chunk_size):  # is chunk overwritten here?
                    if len(data) == chunk_size:
                        yield data
                    else:
                        chunk = data

    if chunk:
        yield chunk


def bufferedfileiter(
    path: PathType,
    chunk_size: int,
    mode: str = "rb",
    encoding: Optional[str] = None,
    errors: Optional[str] = None,
    start: int = 0,
    amount: Optional[int] = None,
    buffer_size: int = FILE_IO_BUFFER_SIZE,
) -> Iterable[Union[str, bytes]]:

    """Iterate over file at `path` reading chunks of size `buffer_size` at a time.
    Yields data chunks of `chunk_size` and optionally limits output to `amount` bytes.
    """

    return resizer(blockfileiter(path, mode, encoding, errors, start, amount, buffer_size), chunk_size)


def byte_out(path: PathType, buffer_size: int = FILE_IO_BUFFER_SIZE) -> Iterable[bytes]:

    """Reads file at `path` byte by byte, using a read buffer of size `buffer_size`."""

    return resizer(blockfileiter(path, mode="rb", chunk_size=buffer_size), 1)


def consume_file(filename: PathType, buffer_size: int = FILE_IO_BUFFER_SIZE) -> None:
    """reads whole file but ignores content"""

    consume(blockfileiter(filename, mode="rb", chunk_size=buffer_size))


# was: same_files, textfile_equal: equal_files(*paths, mode="rt")
def equal_files(
    *paths: PathType,
    mode: str = "rb",
    encoding: Optional[str] = None,
    errors: Optional[str] = None,
    amount: Optional[int] = None,
    chunk_size: int = FILE_IO_BUFFER_SIZE,
) -> bool:

    """Check if files at `*paths` are equal. Chunks of size `chunk_size` are read at a time.
    Data can be optionally limited to `amount`.
    """

    its = tuple(
        blockfileiter(path, mode=mode, encoding=encoding, errors=errors, amount=amount, chunk_size=chunk_size)
        for path in paths
    )
    return iter_equal(*its)


def is_all_byte(fr: IO, thebyte: bytes = b"\0", chunk_size: int = FILE_IO_BUFFER_SIZE) -> bool:

    """Test if file-like `fr` consists only of `thebyte` bytes."""

    assert isinstance(thebyte, bytes)

    thebyte = thebyte * chunk_size
    for data in simple_file_iter(fr, chunk_size):
        if data != thebyte[: len(data)]:
            return False
    return True


def iter_zip(
    file: Union[PathType, IO],
    mode: str = "rb",
    encoding: Optional[str] = None,
    errors: Optional[str] = None,
    newline: Optional[str] = None,
    password: Optional[bytes] = None,
) -> Iterator[Tuple[str, IO]]:

    """
    Iterate file-pointers to archived files. They are valid for one iteration step each.
    If `file` is a file-like, it must be seekable.
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


def iter_7zip(
    file: Union[BinaryIO, PathType],
    mode: str = "rb",
    encoding: Optional[str] = None,
    errors: Optional[str] = None,
    newline: Optional[str] = None,
    password: Optional[str] = None,
) -> Iterator[Tuple[str, IO]]:

    from py7zr import SevenZipFile

    encoding = _check_arguments(mode, encoding)
    newmode = _stripmode(mode)

    with SevenZipFile(file, mode=newmode) as zf:
        for fname, bf in zf.readall().items():
            yield fname, wrap_text(bf, mode, encoding, errors, newline)


def iter_tar(
    file: Union[PathType, BinaryIO],
    mode: str = "rb",
    encoding: Optional[str] = None,
    errors: Optional[str] = None,
    newline: Optional[str] = None,
) -> Iterator[Tuple[str, IO]]:

    """
    Iterate file-pointers to archived files. They are valid for one iteration step each.
    With the correct mode, `file` can be a non-seekable file-like.
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


def iter_lines(
    path: PathType,
    encoding: str = "utf-8",
    errors: str = "strict",
    newline: Optional[str] = None,
    verbose: bool = False,
) -> Iterator[str]:

    """Yield lines from text file. Handles compressed files as well.
    if verbose is True, print a progress bar
    """

    with copen(path, "rt", encoding=encoding, errors=errors, newline=newline) as fr:

        if verbose:
            from tqdm import tqdm

            prev_pos = 0

            fr.seek(0, os.SEEK_END)
            total = fr.tell()
            fr.seek(0, os.SEEK_SET)

            with tqdm(total=total, leave=False, unit="B", unit_scale=True) as pbar:
                while True:  # cannot use `for line in fr` here
                    line = fr.readline()
                    if not line:
                        break
                    cur_pos = fr.tell()
                    pbar.update(cur_pos - prev_pos)
                    yield line
                    prev_pos = cur_pos
        else:
            for line in fr:
                yield line


def iter_stripped(
    path: PathType, encoding: str = "utf-8", errors: str = "strict", newline: Optional[str] = None
) -> Iterator[str]:

    """Yield lines from text file with trailing newlines stripped.
    Handles compressed files as well.
    """

    with copen(path, "rt", encoding=encoding, errors=errors, newline=newline) as fr:
        for line in fr:
            yield line.rstrip("\r\n")


# is this still needed?
def file_byte_reader(
    filename: PathType, inputblocksize: int, outputblocksize: int, DEBUG: bool = True
) -> Iterator[bytes]:

    assert (inputblocksize % outputblocksize == 0) or (
        outputblocksize % inputblocksize == 0
    ), "Neither input nor output size is a multiple of the other"

    bytes_yielded = 0
    bytes = bytearray(max(inputblocksize, outputblocksize))
    bytes_used = 0
    for read in blockfileiter(filename, chunk_size=inputblocksize):
        bytes[bytes_used : bytes_used + len(read)] = read
        # print("read {} bytes to pos [{}:{}]".format(len(read),bytes_used,bytes_used+len(read)))
        bytes_used += len(read)
        pos = 0
        while bytes_used >= outputblocksize:
            yield bytes[pos : pos + outputblocksize]
            bytes_yielded += outputblocksize
            # print("yielded {} bytes from pos [{}:{}]".format(outputblocksize,pos,pos+outputblocksize))
            pos += outputblocksize
            bytes_used -= outputblocksize
    if DEBUG:
        import os.path

        filesize = os.path.getsize(filename)
        if filesize != bytes_yielded:
            print(f"{bytes_yielded} bytes yielded, filesize: {filesize}")
