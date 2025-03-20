import locale
import os
from contextlib import contextmanager
from io import BytesIO, StringIO
from typing import IO, Iterator, Optional

if hasattr(locale, "getencoding"):
    DEFAULT_ENCODING = locale.getencoding()
else:
    DEFAULT_ENCODING = locale.getpreferredencoding(False)


class MemoryPath:
    def __init__(self, data: Optional[bytes] = None) -> None:
        self.data = data

    # Querying file type and status

    def stat(self, *, follow_symlinks: bool = True) -> os.stat_result:
        raise NotImplementedError

    def lstat(self) -> os.stat_result:
        raise NotImplementedError

    def exists(self, *, follow_symlinks: bool = True) -> bool:
        return self.data is not None

    def is_file(self, *, follow_symlinks: bool = True) -> bool:
        return self.data is not None

    def is_dir(self, *, follow_symlinks: bool = True) -> bool:
        return False

    def is_symlink(self) -> bool:
        return False

    def is_junction(self) -> bool:
        return False

    def is_mount(self) -> bool:
        return False

    def is_socket(self) -> bool:
        return False

    def is_fifo(self) -> bool:
        return False

    def is_block_device(self) -> bool:
        return False

    def is_char_device(self) -> bool:
        return False

    def samefile(self, other: "MemoryPath") -> bool:
        return self is other

    # Reading and writing files

    @contextmanager
    def open(
        self,
        mode: str = "r",
        buffering: int = -1,
        encoding: Optional[str] = None,
        errors: Optional[str] = None,
        newline: Optional[str] = None,
    ) -> Iterator[IO]:
        if "w" not in mode and self.data is None:
            raise FileNotFoundError()

        if "b" in mode:
            if encoding is not None or errors is not None or newline is not None:
                raise ValueError("encoding, errors and newline cannot by used for bytes")

            if self.data is None:
                bdata = b""
            else:
                bdata = self.data

            with BytesIO(bdata) as fp:
                yield fp
                self.data = fp.getvalue()
        else:
            if encoding is None:
                encoding = DEFAULT_ENCODING

            if errors is None:
                errors = "strict"

            if self.data is None:
                sdata = ""
            else:
                sdata = self.data.decode(encoding, errors)

            with StringIO(sdata, newline) as fp:
                yield fp
                self.data = fp.getvalue().encode(encoding, errors)

    def read_text(
        self, encoding: Optional[str] = None, errors: Optional[str] = None, newline: Optional[str] = None
    ) -> str:
        # new line param is ignored

        if self.data is None:
            raise FileNotFoundError

        if encoding is None:
            encoding = DEFAULT_ENCODING

        if errors is None:
            errors = "strict"

        return self.data.decode(encoding, errors)

    def read_bytes(self, data: bytes) -> bytes:
        if self.data is None:
            raise FileNotFoundError

        return self.data

    def write_text(self, data: str, encoding=None, errors=None, newline=None) -> None:
        # new line param is ignored

        if encoding is None:
            encoding = DEFAULT_ENCODING

        if errors is None:
            errors = "strict"

        self.data = data.encode(encoding, errors)

    def write_bytes(self, data: bytes) -> None:
        self.data = data
