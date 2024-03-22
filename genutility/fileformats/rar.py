import logging
import os
import subprocess  # nosec
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Union

from ..os import CurrentWorkingDirectory
from ..string import surrounding_join
from ..subprocess import force_decode  # nosec

logger = logging.getLogger(__name__)


class RarError(Exception):
    returncode: int
    cmd: str
    output: str

    def __init__(self, msg: str, returncode: int, cmd: str, output: str) -> None:
        Exception.__init__(self, msg)
        self.returncode = returncode
        self.cmd = cmd
        self.output = output


class WinRarExitCodes(Enum):
    SUCCESS = 0  # Successful operation
    WARNING = 1  # Non fatal error(s) occurred
    FATAL_ERROR = 2  # A fatal error occurred
    CRC_ERROR = 3  # Invalid checksum, data is damaged
    LOCKED_ARCHIVE = 4  # Attempt to modify a locked archive
    WRITE_ERROR = 5  # Write error
    OPEN_ERROR = 6  # Open file error
    USER_ERROR = 7  # Wrong command line option
    MEMORY_ERROR = 8  # Not enough memory
    CREATE_ERROR = 9  # Create file error
    NO_FILES = 10  # No files matching the specified mask and options were found
    BAD_PASS = 11  # Wrong password.
    USER_BREAK = 255  # User stopped the process


@dataclass
class Flag:
    value: bool
    name: str


@dataclass
class Option:
    value: Union[bool, int, str]
    template: str


class Rar:
    windows_executable = Path("C:/Program Files/WinRAR/Rar.exe")
    flags: Dict[str, Flag]
    options: Dict[str, Option]

    def __init__(self, archive: Path, executable: Optional[Path] = None) -> None:
        """archive: archive to work with, everything which is supported by winrar
        executable: path/to/Rar.exe"""

        self.exe = executable or self.windows_executable

        if not self.exe.is_file():
            raise ValueError("Invalid executable")

        self.archive = archive
        self.filelist: List[str] = []
        self.cmd = ""
        self.flags = {}
        self.flags["lock"] = Flag(False, "k")
        self.flags["delete"] = Flag(False, "df")
        self.flags["test"] = Flag(False, "t")
        self.flags["filetime"] = Flag(False, "tl")
        self.flags["append_archive_name"] = Flag(False, "ad")
        self.options = {}
        self.options["split"] = Option(False, "v%s")
        self.options["compression"] = Option(False, "m%u")
        self.options["password"] = Option(False, "p%s")
        self.options["password_header"] = Option(False, "hp%s")
        self.options["recovery"] = Option(False, "rr%up")
        self.options["recovery_volumes"] = Option(False, "rr%u%%")

    def add_file(self, pathname: str) -> None:
        self.filelist.append(pathname)

    def add_files(self, filelist: Iterable[str]) -> None:
        self.filelist.extend(filelist)

    def set_compression(self, level: Union[int, bool]) -> None:
        """level: 0 store, 1 fastest, 2 fast, 3 normal, 4 good, 5 best (default: 3)"""

        if level not in range(0, 6) and level is not False:
            raise ValueError("Invalid parameter: Set compression level (0-store...3-default...5-best)")
        self.options["compression"].value = level

    def set_password(self, password, encrypt_filenames: bool = False) -> None:
        if encrypt_filenames:
            self.options["password_header"].value = password
            self.options["password"].value = False
        else:
            self.options["password"].value = password
            self.options["password_header"].value = False

    def add_recovery_info(self, rr: int) -> None:
        """rr: recovery record in percent, only 1-10 is valid"""

        if rr < 1 or rr > 10:
            raise ValueError("Only 1%-10% valid")
        self.options["recovery"].value = rr

    def add_recovery_volumes(self, rv: int) -> None:
        """rv: number of recovery volumes"""

        self.options["recovery_volumes"].value = rv

    def split(self, split: str):
        self.options["split"].value = split

    def lock(self, flag: bool = True) -> None:
        self.flags["lock"].value = flag

    def delete_after_archiving(self, flag: bool = True) -> None:
        """flag (bool): delete files after archiving"""

        self.flags["delete"].value = flag

    def test_after_archiving(self, flag: bool = True) -> None:
        """flag (bool): test archive after archiving"""

        self.flags["test"].value = flag

    def set_archive_to_filetime(self, flag: bool = True) -> None:
        self.flags["filetime"].value = flag

    def commandline(self, cmd: str) -> None:
        self.cmd = cmd.strip()

    def _execute(self, args: str) -> str:
        cmd = f"{self.exe} {args}"
        try:
            ret = subprocess.check_output(cmd, stderr=subprocess.STDOUT, cwd=os.getcwd())  # nosec
        except subprocess.CalledProcessError as e:
            output = force_decode(e.output)
            raise RarError(
                f"Calling `{e.cmd}` failed with error code {e.returncode}", e.returncode, e.cmd, output
            )  # should use only stderr

        return force_decode(ret)

    def test(self, password: str = "-") -> None:  # nosec
        self._execute(f't -p{password} "{self.archive}"')

    def get_files_str(self) -> str:
        return surrounding_join(" ", self.filelist, '"', '"')

    def get_flag_str(self) -> str:
        return surrounding_join(" ", [value.name for value in self.flags.values() if value.value is True], "-", "")

    def get_options_str(self) -> str:
        return surrounding_join(
            " ", [value.template % value.value for value in self.options.values() if value.value is not False], "-", ""
        )

    def _get_args(self, command: str) -> str:
        return f'{command} {self.get_flag_str()} {self.get_options_str()} {self.cmd} "{self.archive}" {self.get_files_str()}'

    def create(self) -> None:
        self._execute(self._get_args("a"))

    def extract(self, directory: str, mode: int = 0) -> None:
        self.filelist = [directory]
        if mode == 1:
            self.flags["append_archive_name"].value = True
        self._execute(self._get_args("x"))

    def close(self) -> None:
        pass


def create_rar_from_folder(
    path: Path,
    dest_path: Optional[Path] = None,
    profile_setter_func: Optional[Callable] = None,
    filter_func: Callable = lambda x: True,
    name_transform: Callable = lambda x: x,
) -> bool:
    if not path.is_dir():
        return False

    if dest_path is None:
        dest_path = path.parent

    with CurrentWorkingDirectory(path):
        try:
            r = Rar(dest_path / f"{name_transform(path.name)}.rar")
            if profile_setter_func:
                profile_setter_func(r)
            with os.scandir(".") as it:
                for entry in filter(filter_func, it):  # was: scandir_rec
                    r.add_file(entry.path)
            r.create()
        except RarError as e:
            logger.error(f"{str(e)}\n{e.output}")
            return False

    return True


_CWD_PATH = Path(".")


def create_rar_from_file(
    path: Path,
    dest_path: Path = _CWD_PATH,
    profile_setter_func: Optional[Callable[[Rar], Any]] = None,
    name_transform: Callable = lambda x: x,
) -> bool:
    if dest_path == ".":
        dest_path = path.parent

    with CurrentWorkingDirectory(path.parent):
        try:
            r = Rar(dest_path / f"{name_transform(path.name)}.rar")
            if profile_setter_func:
                profile_setter_func(r)
            r.add_file(path.name)
            r.create()
        except RarError as e:
            logger.error(f"{str(e)}\n{e.output}")
            return False

    return True
