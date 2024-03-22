from os import remove
from tempfile import NamedTemporaryFile
from typing import Optional

from .file import _check_arguments


class CloseableNamedTemporaryFile:

    def __init__(self, mode: str = "w+b", encoding: Optional[str] = None) -> None:
        encoding = _check_arguments(mode, encoding)
        self.f = NamedTemporaryFile(mode=mode, encoding=encoding, delete=False)

    def __enter__(self):
        self.f.__enter__()
        return self.f, self.f.name

    def __exit__(self, exc_type, exc_value, traceback):
        self.f.__exit__(exc_type, exc_value, traceback)
        remove(self.f.name)
