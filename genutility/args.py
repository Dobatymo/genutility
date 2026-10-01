import os
import os.path
import shlex
import stat
import sys
from argparse import ArgumentParser, ArgumentTypeError, Namespace
from codecs import lookup
from datetime import date, datetime
from functools import wraps
from math import isfinite
from pathlib import Path
from typing import Any, Callable, Optional, Union

from .os import islink


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


def arg_to_path(func: Callable[[Path], Path]) -> Callable[[str], Path]:
    @wraps(func)
    def inner(path):
        return func(Path(path))

    return inner


def int_at_least(minimum: int) -> Callable[[str], int]:
    from builtins import int as builtin_int

    def int(s: str) -> builtin_int:  # see: multiple_of()
        number = builtin_int(s)

        if number < minimum:
            raise ArgumentTypeError(f"{s} is less than {minimum}")

        return number

    return int


non_negative_int = int_at_least(0)
positive_int = int_at_least(1)


def datetime_iso(s: str) -> datetime:
    """Parse an ISO 8601 datetime, including reduced-precision times."""
    value = s
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"

    for fmt in ("%Y-%m-%dT%H", "%Y-%m-%dT%H:%M"):
        try:
            # A reduced-precision ISO value has no timezone from which to construct an aware datetime.
            return datetime.strptime(s, fmt)  # noqa: DTZ007
        except ValueError:
            pass

    try:
        return datetime.fromisoformat(value)
    except ValueError as e:
        raise ArgumentTypeError(f"{s!r} is not a valid ISO 8601 datetime") from e


def date_iso(s: str) -> date:
    try:
        return date.fromisoformat(s)
    except ValueError as e:
        raise ArgumentTypeError("must be YYYY-MM-DD") from e


_BYTE_SIZE_SUFFIXES = "KMGTPEZY"


def _byte_size(s: str, base: int) -> int:
    suffix = s[-1:]
    if suffix in _BYTE_SIZE_SUFFIXES:
        number = s[:-1]
        exponent = _BYTE_SIZE_SUFFIXES.index(suffix) + 1
    else:
        number = s
        exponent = 0

    if not number.isascii() or not number.isdecimal():
        raise ArgumentTypeError(
            f"{s!r} is not an unsigned integer byte size with an optional K/M/G/T/P/E/Z/Y suffix (base {base})"
        )

    return int(number) * base**exponent


def byte_size_si(s: str) -> int:
    return _byte_size(s, 1000)


def byte_size_iec(s: str) -> int:
    return _byte_size(s, 1024)


def finite_float(s: str) -> float:
    number = float(s)

    if not isfinite(number):
        raise ArgumentTypeError(f"{s} is not finite")

    return number


def non_negative_float(s: str) -> float:
    number = finite_float(s)

    if number < 0:
        raise ArgumentTypeError(f"{s} is negative")

    return number


def positive_float(s: str) -> float:
    number = finite_float(s)

    if number <= 0:
        raise ArgumentTypeError(f"{s} is not positive")

    return number


def encoding_name(s: str) -> str:
    try:
        lookup(s)
    except LookupError as e:
        raise ArgumentTypeError(f"{s} is not a valid encoding") from e

    return s


def multiple_of(divisor: int, *, minimum: Optional[int] = None) -> Callable[[str], int]:
    from builtins import int as builtin_int

    """ This function is called 'int' so that argparse can show a nicer error message
        in case input cannot be cast to int:
        error: argument --multiple: invalid int value: 'a'
    """

    if divisor == 0:
        raise ValueError("divisor cannot be zero")

    def int(s: str) -> builtin_int:
        number = builtin_int(s)

        if minimum is not None and number < minimum:
            raise ArgumentTypeError(f"{s} is less than {minimum}")

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
    """Checks if `s` is a valid suffix with a leading dot."""

    if len(s) <= 1 or not s.startswith("."):
        msg = f"{s} is not a valid suffix. It must start with a dot."
        raise ArgumentTypeError(msg)

    return s


def suffix_raw(s: str) -> str:
    """Checks if `s` is a valid suffix which starts with a dot,
    but returns it without the dot.
    """

    if len(s) <= 1 or not s.startswith("."):
        msg = f"{s} is not a valid suffix. It must start with a dot."
        raise ArgumentTypeError(msg)

    return s[1:]


def lowercase(s: str) -> str:
    """Converts argument to lowercase."""

    return s.lower()


def suffix_lower(s: str) -> str:
    return lowercase(suffix(s))


def suffix_lower_raw(s: str) -> str:
    return lowercase(suffix_raw(s))


def _stat_path(path: Path, *, follow_symlinks: bool) -> Optional[os.stat_result]:
    try:
        return os.stat(path, follow_symlinks=follow_symlinks)
    except FileNotFoundError:
        return None
    except OSError as e:
        raise ArgumentTypeError(f"cannot inspect {path}: {e}") from e


def _is_link(path: Path) -> bool:
    try:
        return islink(path)
    except OSError as e:
        raise ArgumentTypeError(f"cannot inspect {path}: {e}") from e


def _path_stat(path: Path, follow_links: bool) -> Optional[os.stat_result]:
    entry_stat = _stat_path(path, follow_symlinks=False)
    if entry_stat is None:
        return None

    if _is_link(path):
        if not follow_links:
            raise ArgumentTypeError(f"{path} is a symbolic link, junction, or reparse point")
        return _stat_path(path, follow_symlinks=True)

    return entry_stat


def _existing_path(path: Path, follow_links: bool) -> Path:
    if _path_stat(path, follow_links) is None:
        msg = f"{path} does not exist"
        raise ArgumentTypeError(msg)

    return path


@arg_to_path
def existing_path(path: Path) -> Path:
    """Checks if a path exists, following links."""

    return _existing_path(path, True)


@arg_to_path
def existing_path_nofollow(path: Path) -> Path:
    """Checks if a path exists without allowing a link-like final component."""

    return _existing_path(path, False)


@arg_to_path
def path_nofollow(path: Path) -> Path:
    """Accepts an existing or missing path without allowing a link-like final component."""

    _path_stat(path, False)
    return path


@arg_to_path
def new_path(path: Path) -> Path:
    """Checks that a path does not exist."""

    entry_stat = _stat_path(path, follow_symlinks=False)
    if entry_stat is not None:
        if _is_link(path):
            raise ArgumentTypeError(f"{path} is a symbolic link, junction, or reparse point")
        msg = f"{path} already exists"
        raise ArgumentTypeError(msg)

    return path


def _is_dir(path: Path, follow_links: bool) -> Path:
    path_stat = _path_stat(path, follow_links)
    if path_stat is None or not stat.S_ISDIR(path_stat.st_mode):
        msg = f"{path} is not a directory"
        raise ArgumentTypeError(msg)

    return path


@arg_to_path
def is_dir(path: Path) -> Path:
    """Checks if a path is a directory, following links."""

    return _is_dir(path, True)


@arg_to_path
def is_dir_nofollow(path: Path) -> Path:
    """Checks if a path is a directory without allowing a link-like final component."""

    return _is_dir(path, False)


@arg_to_path
def is_dir_or_new_nofollow(path: Path) -> Path:
    """Accepts a directory or missing path without allowing a link-like final component."""

    path_stat = _path_stat(path, False)
    if path_stat is not None and not stat.S_ISDIR(path_stat.st_mode):
        raise ArgumentTypeError(f"{path} is not a directory")

    return path


@arg_to_path
def relative_path(path: Path) -> Path:
    """Checks that a path is relative."""

    if path.is_absolute():
        raise ArgumentTypeError(f"{path} is absolute")

    return path


def _is_file(path: Path, follow_links: bool) -> Path:
    path_stat = _path_stat(path, follow_links)
    if path_stat is None or not stat.S_ISREG(path_stat.st_mode):
        msg = f"{path} is not a file"
        raise ArgumentTypeError(msg)

    return path


@arg_to_path
def is_file(path: Path) -> Path:
    """Checks if a path is a regular file, following links."""

    return _is_file(path, True)


@arg_to_path
def is_file_nofollow(path: Path) -> Path:
    """Checks if a path is a regular file without allowing a link-like final component."""

    return _is_file(path, False)


@arg_to_path
def is_file_or_new_nofollow(path: Path) -> Path:
    """Accepts a regular file or missing path without allowing a link-like final component."""

    path_stat = _path_stat(path, False)
    if path_stat is not None and not stat.S_ISREG(path_stat.st_mode):
        raise ArgumentTypeError(f"{path} is not a file")

    return path


def _is_file_or_dir(path: Path, follow_links: bool) -> Path:
    path_stat = _path_stat(path, follow_links)
    if path_stat is None or not (stat.S_ISREG(path_stat.st_mode) or stat.S_ISDIR(path_stat.st_mode)):
        msg = f"{path} is not a file or directory"
        raise ArgumentTypeError(msg)

    return path


@arg_to_path
def is_file_or_dir(path: Path) -> Path:
    """Checks if a path is a regular file or directory, following links."""

    return _is_file_or_dir(path, True)


@arg_to_path
def is_file_or_dir_nofollow(path: Path) -> Path:
    """Checks if a path is a regular file or directory without allowing a link-like final component."""

    return _is_file_or_dir(path, False)


@arg_to_path
def future_file(path: Path) -> Path:
    """Tests if file can be created to catch errors early.
    Checks if directory is writeable and file does not exist yet.
    """

    new_path(path)

    parent_stat = _path_stat(path.parent, True)
    if parent_stat is None or not stat.S_ISDIR(parent_stat.st_mode):
        msg = f"directory {path.parent} does not exist"
        raise ArgumentTypeError(msg)
    if not os.access(str(path.parent), os.W_OK):
        msg = f"cannot access directory {path.parent}"
        raise ArgumentTypeError(msg)
    return path


def _empty_dir(dirname: Path, follow_links: bool) -> Path:
    from .iter import is_empty

    _is_dir(dirname, follow_links)
    try:
        with os.scandir(dirname) as it:
            if not is_empty(it):
                msg = f"directory {dirname} is not empty"
                raise ArgumentTypeError(msg)
    except OSError as e:
        raise ArgumentTypeError(f"cannot inspect directory {dirname}: {e}") from e

    return dirname


@arg_to_path
def empty_dir(dirname: Path) -> Path:
    """Checks if a directory is empty, following links."""

    return _empty_dir(dirname, True)


@arg_to_path
def empty_dir_nofollow(dirname: Path) -> Path:
    """Checks if a directory is empty without allowing a link-like final component."""

    return _empty_dir(dirname, False)


def _json_file(path: Union[str, Path], follow_links: bool) -> Any:
    from json import JSONDecodeError

    from .json import read_json

    try:
        return read_json(_is_file(Path(path), follow_links))
    except (JSONDecodeError, OSError, UnicodeError) as e:
        raise ArgumentTypeError(f"{type(e).__name__}: {e}") from e


def json_file(path: Union[str, Path]) -> Any:
    """Reads a JSON file, following links."""

    return _json_file(path, True)


def json_file_nofollow(path: Union[str, Path]) -> Any:
    """Reads a JSON file without allowing a link-like final component."""

    return _json_file(path, False)


def base64_bytes(s: str) -> bytes:
    """Checks if `s` is a valid base64 and decodes it."""
    from base64 import b64decode

    try:
        return b64decode(s, validate=True)
    except ValueError:
        msg = f"{s} is not valid base64"
        raise ArgumentTypeError(msg) from None


def base64_str(s: str) -> str:
    """Checks if `s` is valid base64 and returns it unchanged."""
    base64_bytes(s)
    return s


def base32_bytes(s: str) -> bytes:
    """Checks if `s` is valid base32 and decodes it, accepting lowercase input."""
    from base64 import b32decode

    try:
        return b32decode(s, casefold=True)
    except ValueError:
        msg = f"{s} is not valid base32"
        raise ArgumentTypeError(msg) from None


def base32_str(s: str) -> str:
    """Checks if `s` is valid base32 and returns it unchanged, accepting lowercase input."""
    base32_bytes(s)
    return s


def hex_bytes(length: int) -> Callable[[str], bytes]:
    """Returns an argument type for exactly `length` bytes encoded as hexadecimal."""
    from builtins import bytes as builtin_bytes
    from string import hexdigits

    if length < 0:
        raise ValueError("length cannot be negative")

    def bytes(s: str) -> builtin_bytes:
        if len(s) != length * 2 or not s.isascii() or not all(c in hexdigits for c in s):
            raise ArgumentTypeError(f"value must contain exactly {length * 2} hexadecimal digits")

        return builtin_bytes.fromhex(s)

    return bytes


def ascii(s: str) -> str:
    """Checks if `s` is a valid ascii."""
    try:
        s.encode("ascii")
    except UnicodeEncodeError:
        msg = f"{s} is not valid ascii"
        raise ArgumentTypeError(msg) from None

    return s


def make_arg_type(pattern: str, msg: str, *, group: Optional[int] = None, flags: int = 0) -> Callable:
    import re

    p = re.compile(pattern, flags)

    def inner(s: str) -> str:
        m = p.search(s)
        if m is None:
            raise ArgumentTypeError(msg)

        if group is None:
            return s
        else:
            return m.group(group)

    return inner


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
