from msvcrt import get_osfhandle, open_osfhandle
from os import fdopen
from typing import Optional

from cwinsdk.um.handleapi import CloseHandle
from cwinsdk.um.winnt import GENERIC_READ, GENERIC_WRITE
from typing_extensions import Self

_mode2access = {"": 0, "r": GENERIC_READ, "w": GENERIC_WRITE, "w+": GENERIC_READ | GENERIC_WRITE}


class WindowsHandle:
    def __init__(self, handle: int, doclose: bool = True, timeout_ms: Optional[int] = None) -> None:
        if not isinstance(handle, int):
            raise ValueError("handle must be an int")

        self.handle = handle
        self.doclose = doclose
        self.timeout_ms = timeout_ms

    @property
    def overlapped(self) -> True:
        return self.timeout_ms is not None

    @classmethod
    def from_file(cls, fp):
        return cls.from_fd(fp.fileno())

    @classmethod
    def from_fd(cls, fd):
        return cls(get_osfhandle(fd), doclose=False)

    def get_fd(self, flags):
        return open_osfhandle(self.handle, flags)

    def get_file(self, flags, mode="r", buffering=-1, encoding=None, errors=None, newline=None, closefd=True):
        return fdopen(self.get_fd(flags), mode, buffering, encoding, errors, newline, closefd)

    def close(self) -> None:
        CloseHandle(self.handle)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.doclose:
            self.close()
