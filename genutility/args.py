from __future__ import generator_stop

import os
import os.path
import shlex
import sys
from argparse import ArgumentParser, ArgumentTypeError, Namespace
from functools import wraps
from os import makedirs
from pathlib import Path
from typing import Any, Callable, Union


def get_args(argparser: ArgumentParser) -> Namespace:
    """get commandline arguments from std input instead"""

    from pprint import pprint

    from .stdio import confirm

    if len(sys.argv) > 1:
        return argparser.parse_args()

    print("stdin")
    args = []

    for action in argparser._actions:
        pprint(action)

    for k, v in argparser._option_string_actions.items():

        nargs = v.nargs if v.nargs is not None else 1

        if nargs == 0:
            if confirm(str(k)):
                args.append(k)
        else:
            instr = input(f"{k} ({nargs}): ")  # separate multiple value by whitespace, quoting supported.
            args.append(k)
            args.append(instr)

    args = shlex.split(" ".join(args))
    pprint(args)
    return argparser.parse_args(args)


def arg_to_path(func: Callable[[Path], Path]) -> Callable:
    @wraps(func)
    def inner(path):
        return func(Path(path))

    return inner


def multiple_of(divisor: int) -> Callable[[str], int]:

    from builtins import int as builtin_int

    """ This function is called 'int' so that argparse can show a nicer error message
        in case input cannot be cast to int:
        error: argument --multiple: invalid int value: 'a'
    """

    def int(s: str) -> builtin_int:

        number = builtin_int(s)

        if number % divisor != 0:
            msg = f"{s} is not clearly divisible by {divisor}"
            raise ArgumentTypeError(msg)

        return number

    return int


def in_range(start: int, stop: int, step: int = 1) -> Callable[[str], int]:

    from builtins import int as builtin_int

    def int(s: str) -> builtin_int:  # see: multiple_of()

        number = builtin_int(s)

        r = range(start, stop, step)
        if number not in r:
            msg = f"{s} is not in {r}"
            raise ArgumentTypeError(msg)

        return number

    return int


def between(start: float, stop: float) -> Callable[[str], float]:

    from builtins import float as builtin_float

    def float(s: str) -> builtin_float:

        number = builtin_float(s)

        if not (start <= number < stop):
            msg = f"{s} is not in between {start} and {stop}"
            raise ArgumentTypeError(msg)

        return number

    return float


def suffix(s: str) -> str:

    """Checks if `s` is a valid suffix."""

    if not s.startswith("."):
        msg = f"{s} is not a valid suffix. It must start with a dot."
        raise ArgumentTypeError(msg)

    return s


def lowercase(s: str) -> str:

    """Converts argument to lowercase."""

    return s.lower()


def suffix_lower(s: str) -> str:
    return lowercase(suffix(s))


@arg_to_path
def existing_path(path: Path) -> Path:

    """Checks if a path exists."""

    if not path.exists():
        msg = f"{path} does not exist"
        raise ArgumentTypeError(msg)

    return path


@arg_to_path
def new_path(path: Path) -> Path:

    """Checks if a path exists."""

    if path.exists():
        msg = f"{path} already exists"
        raise ArgumentTypeError(msg)

    return path


@arg_to_path
def is_dir(path: Path) -> Path:

    """Checks if a path is an actual directory"""

    if not path.is_dir():
        msg = f"{path} is not a directory"
        raise ArgumentTypeError(msg)

    return path


@arg_to_path
def abs_path(path: Path) -> Path:

    """Checks if a path is an actual directory"""

    return path.resolve()


@arg_to_path
def is_file(path: Path) -> Path:

    """Checks if a path is an actual file"""

    if not path.is_file():
        msg = f"{path} is not a file"
        raise ArgumentTypeError(msg)

    return path


@arg_to_path
def future_file(path: Path) -> Path:

    """Tests if file can be created to catch errors early.
    Checks if directory is writeable and file does not exist yet.
    """

    if path.parent and not os.access(str(path.parent), os.W_OK):
        msg = f"cannot access directory {path.parent}"
        raise ArgumentTypeError(msg)
    if path.is_file():
        msg = f"file {path} already exists"
        raise ArgumentTypeError(msg)
    return path


@arg_to_path
def out_dir(path: Path) -> Path:

    """Tests if `path` is a directory. If not it tries to create one."""

    if not path.is_dir():
        try:
            makedirs(path)
        except OSError:
            msg = f"Error: '{path}' is not a valid directory."
            raise ArgumentTypeError(msg)

    return path


@arg_to_path
def empty_dir(dirname: Path) -> Path:

    """tests if directory is empty"""

    from .iter import is_empty

    with os.scandir(dirname) as it:
        if not is_empty(it):
            msg = f"directory {dirname} is not empty"
            raise ArgumentTypeError(msg)

    return dirname


def json_file(path: Union[str, Path]) -> Any:
    from json import JSONDecodeError

    from .json import read_json

    try:
        return read_json(path)
    except JSONDecodeError as e:
        raise ArgumentTypeError(f"JSONDecodeError: {e}")


if __name__ == "__main__":

    parser = ArgumentParser()
    parser.add_argument("--str")
    parser.add_argument("--required", action="store_true")
    parser.add_argument("--add", nargs="+")
    print(get_args(parser))

    """
    parser = ArgumentParser()
    parser.add_argument('--indir', type=is_dir)
    parser.add_argument('--infile', type=is_file)
    parser.add_argument('--outfile', type=future_file)
    parser.add_argument('--outdir', type=empty_dir)
    args = parser.parse_args()
    print(args)
    """
