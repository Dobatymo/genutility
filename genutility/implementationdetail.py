from __future__ import generator_stop

from inspect import currentframe, getfile, getouterframes, getsourcefile
from pathlib import Path
from sys import _getframe  # sys._getframe() is not guaranteed to exist
from typing import Sequence, Union


def get_calling_functions(level: Union[int, Sequence[int]] = 2, sep: str = "->") -> str:
    curframe = currentframe()
    if curframe is None:
        raise RuntimeError("This Python interpreter does not provide stack frame support")

    calframe = getouterframes(curframe)
    del curframe

    if isinstance(level, int):
        return f"{Path(calframe[level].filename).stem}:{calframe[level].function}"
    else:
        return sep.join(f"{Path(calframe[level].filename).stem}:{calframe[level].function}" for level in level)


def caller_file(depth: int = 1) -> Path:
    return Path(getfile(_getframe(depth))).resolve().parent


def caller_sourcefile(depth: int = 1) -> Path:
    return Path(getsourcefile(_getframe(depth))).resolve().parent
