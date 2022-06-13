from __future__ import generator_stop

import os.path
from os import PathLike, fspath, remove, replace
from tempfile import mkstemp
from typing import IO, ContextManager, Optional, Union

from .file import copen

PathType = Union[str, PathLike]

# http://stupidpythonideas.blogspot.tw/2014/07/getting-atomic-writes-right.html
class TransactionalCreateFile:
    def __init__(
        self,
        path: PathType,
        mode: str = "wb",
        encoding: Optional[str] = None,
        errors: Optional[str] = None,
        newline: Optional[str] = None,
        prefix: str = "tmp",
        handle_archives: bool = True,
    ) -> None:

        is_text = "t" in mode

        self.path = fspath(path)
        suffix = os.path.splitext(self.path)[1].lower()
        curdir = os.path.dirname(self.path)
        fd, self.tmppath = mkstemp(suffix, prefix, curdir, is_text)
        self.fp = copen(
            fd, mode, encoding=encoding, errors=errors, newline=newline, ext=suffix, handle_archives=handle_archives
        )

    def commit(self) -> None:

        self.fp.close()
        replace(self.tmppath, self.path)  # should be atomic

    def rollback(self) -> None:

        self.fp.close()
        remove(self.tmppath)

    def __enter__(self) -> IO:

        return self.fp

    def __exit__(self, exc_type, exc_value, traceback):
        # at this point the original file is unmodified and the new file exists as tempfile on disk (or in buffer on windows)
        if exc_type:
            self.rollback()
        else:
            self.commit()


def sopen(
    path: PathType,
    mode: str = "rb",
    encoding: Optional[str] = None,
    errors: Optional[str] = None,
    newline: Optional[str] = None,
    safe: bool = False,
) -> ContextManager[IO]:

    if safe:
        return TransactionalCreateFile(path, mode, encoding=encoding, errors=errors, newline=newline)
    else:
        return copen(path, mode, encoding=encoding, errors=errors, newline=newline)


def write_file(
    data: Union[str, bytes],
    path: PathType,
    mode: str = "wb",
    encoding: Optional[str] = None,
    errors: Optional[str] = None,
    newline: Optional[str] = None,
) -> None:

    """Writes/overwrites files in a safe way. That means either the original file
    will be left untouched, or it will be replaced with the complete new file.
    """

    with TransactionalCreateFile(path, mode, encoding=encoding, errors=errors, newline=newline) as fw:
        fw.write(data)
