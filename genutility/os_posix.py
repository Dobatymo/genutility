import fcntl
import os
import signal
from typing import IO

from .os_shared import _usagetuple


def _lock(fp: IO, exclusive: bool = True, block: bool = False) -> None:
    if exclusive:
        operation = fcntl.LOCK_EX
    else:
        operation = fcntl.LOCK_SH

    if not block:
        operation |= fcntl.LOCK_NB

    fcntl.flock(fp, operation)


def _unlock(fp: IO) -> None:
    fcntl.flock(fp, fcntl.LOCK_UN)


def _disk_usage_posix(path: str) -> _usagetuple:
    st = os.statvfs(path)

    total = st.f_blocks * st.f_frsize
    free = st.f_bavail * st.f_frsize

    return _usagetuple(total, total - free, free)


def _interrupt_posix() -> None:
    os.kill(os.getpid(), signal.SIGINT)


def _filemanager_cmd_posix(path: str) -> str:
    return f'nautilus "{path}"'  # gnome only. xdg-open for the rest?


def _get_appdata_dir(roaming: bool = False) -> str:
    return os.getenv("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
