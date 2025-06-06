import logging
import os
import signal
from ctypes import byref, c_wchar_p, cast, create_unicode_buffer, memset, sizeof
from ctypes.wintypes import DWORD, HANDLE, LPCWSTR, ULARGE_INTEGER
from enum import IntFlag
from msvcrt import get_osfhandle
from typing import IO, Union

from cwinsdk.shared.ehstorioctl import MAX_PATH
from cwinsdk.shared.ntdef import PWSTR
from cwinsdk.um import fileapi, winnt
from cwinsdk.um.combaseapi import CoTaskMemFree
from cwinsdk.um.consoleapi import ENABLE_VIRTUAL_TERMINAL_PROCESSING, GetConsoleMode, SetConsoleMode
from cwinsdk.um.knownfolders import FOLDERID_LocalAppData, FOLDERID_RoamingAppData
from cwinsdk.um.minwinbase import LOCKFILE_EXCLUSIVE_LOCK, LOCKFILE_FAIL_IMMEDIATELY, OVERLAPPED
from cwinsdk.um.processenv import GetStdHandle
from cwinsdk.um.shlobj_core import SHGetKnownFolderPath
from cwinsdk.um.winbase import STD_OUTPUT_HANDLE

from .os_shared import _usagetuple, _volumeinfotuple

PathType = Union[str, os.PathLike]


class FileAttributes(IntFlag):
    READONLY = winnt.FILE_ATTRIBUTE_READONLY
    HIDDEN = winnt.FILE_ATTRIBUTE_HIDDEN
    SYSTEM = winnt.FILE_ATTRIBUTE_SYSTEM
    DIRECTORY = winnt.FILE_ATTRIBUTE_DIRECTORY
    ARCHIVE = winnt.FILE_ATTRIBUTE_ARCHIVE
    DEVICE = winnt.FILE_ATTRIBUTE_DEVICE
    NORMAL = winnt.FILE_ATTRIBUTE_NORMAL
    TEMPORARY = winnt.FILE_ATTRIBUTE_TEMPORARY
    SPARSE_FILE = winnt.FILE_ATTRIBUTE_SPARSE_FILE
    REPARSE_POINT = winnt.FILE_ATTRIBUTE_REPARSE_POINT
    COMPRESSED = winnt.FILE_ATTRIBUTE_COMPRESSED
    OFFLINE = winnt.FILE_ATTRIBUTE_OFFLINE
    NOT_CONTENT_INDEXED = winnt.FILE_ATTRIBUTE_NOT_CONTENT_INDEXED
    ENCRYPTED = winnt.FILE_ATTRIBUTE_ENCRYPTED
    INTEGRITY_STREAM = winnt.FILE_ATTRIBUTE_INTEGRITY_STREAM
    VIRTUAL = winnt.FILE_ATTRIBUTE_VIRTUAL
    NO_SCRUB_DATA = winnt.FILE_ATTRIBUTE_NO_SCRUB_DATA
    EA = winnt.FILE_ATTRIBUTE_EA
    PINNED = winnt.FILE_ATTRIBUTE_PINNED
    UNPINNED = winnt.FILE_ATTRIBUTE_UNPINNED
    RECALL_ON_OPEN = winnt.FILE_ATTRIBUTE_RECALL_ON_OPEN
    RECALL_ON_DATA_ACCESS = winnt.FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS


def get_stdout_handle() -> HANDLE:
    """Might return a redirect handle. For the real handle, use CreateFile("CONOUT$")"""

    return GetStdHandle(STD_OUTPUT_HANDLE)


class EnableAnsi:  # doesn't work for some reason...
    def __init__(self) -> None:
        # os.system("") # calls cmd, which sets ANSI mode, but doesn't disable it when exiting (it's a bug probably)
        self.handle = get_stdout_handle()
        self.oldmode = DWORD()

        GetConsoleMode(self.handle, byref(self.oldmode))
        SetConsoleMode(self.handle, self.oldmode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING)

    def close(self) -> None:
        SetConsoleMode(self.handle, self.oldmode.value)

    def __enter__(self) -> None:
        return None

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


def _file_attributes(path: str) -> FileAttributes:
    return FileAttributes(fileapi.GetFileAttributesW(path))


def _islink(path: PathType) -> bool:
    """Tests if `path` refers to a symlink or a junction.
    - Python >= 3.2 `os.path.islink()` only supports symlinks, not junctions.
    - Python < 3.2 `os.path.islink()` always returns `False` on Windows.
    This function works in all cases.
    """

    # this can be replaced with a os.stat() based implementation for Python 3.8+

    filename = os.fspath(path)
    attributes = fileapi.GetFileAttributesW(filename)

    return attributes & winnt.FILE_ATTRIBUTE_REPARSE_POINT == winnt.FILE_ATTRIBUTE_REPARSE_POINT


def _realpath(path: PathType) -> str:
    """Partial fix for os.path.realpath() which doesn't work under Win7 for python < 3.8.
    This fails when it needs to concat a absolute unc path to a relative path. normpath doesn't normalize it then.
    """

    prefix = "\\\\?\\"
    _path = os.fspath(path)
    if _path.startswith(prefix):
        _path = _path[4:]
        was_dos_device_path = True
    else:
        was_dos_device_path = False
    _path = os.path.abspath(_path)
    if _islink(_path):
        _path = os.path.normpath(os.path.join(os.path.dirname(_path), os.readlink(_path)))
    if was_dos_device_path:
        _path = prefix + _path
    return _path


def _get_mount_path(path: str) -> str:
    FileName = LPCWSTR(path)
    BufferLength = 50  # MSDN suggestion
    VolumeName = create_unicode_buffer(BufferLength)
    fileapi.GetVolumeNameForVolumeMountPointW(FileName, VolumeName, BufferLength)
    return VolumeName.value


def _lock(fp: IO, exclusive: bool = True, block: bool = False) -> None:
    fd = fp.fileno()
    handle = get_osfhandle(fd)

    flags = 0
    if exclusive:
        flags |= LOCKFILE_EXCLUSIVE_LOCK
    if not block:
        flags |= LOCKFILE_FAIL_IMMEDIATELY

    overlapped = OVERLAPPED()
    memset(byref(overlapped), 0, sizeof(overlapped))

    fileapi.LockFileEx(handle, flags, 0, 0xFFFFFFFF, 0xFFFFFFFF, overlapped)


def _unlock(fp: IO) -> None:
    fd = fp.fileno()
    handle = get_osfhandle(fd)

    overlapped = OVERLAPPED()
    memset(byref(overlapped), 0, sizeof(overlapped))

    fileapi.UnlockFileEx(handle, 0, 0xFFFFFFFF, 0xFFFFFFFF, overlapped)


def _get_appdata_dir(roaming: bool = False) -> str:
    if roaming:
        folderid = FOLDERID_RoamingAppData
    else:
        folderid = FOLDERID_LocalAppData

    KF_FLAG_CREATE = 0x00008000

    rfid = byref(folderid)
    Flags = KF_FLAG_CREATE
    Token = None
    Path = PWSTR()

    try:
        result = SHGetKnownFolderPath(rfid, Flags, Token, byref(Path))
    except OSError:
        logging.error(f"SHGetKnownFolderPath result: {result & 0xFFFFFFFF:X}")
        raise

    ret = cast(Path, c_wchar_p).value
    CoTaskMemFree(Path)
    assert ret
    return ret


def _disk_usage_windows(path: str) -> _usagetuple:
    DirectoryName = LPCWSTR(path)
    FreeBytesAvailableToCaller = ULARGE_INTEGER(0)  # user free
    TotalNumberOfBytes = ULARGE_INTEGER(0)  # user total
    TotalNumberOfFreeBytes = None  # total free

    fileapi.GetDiskFreeSpaceExW(
        DirectoryName, byref(FreeBytesAvailableToCaller), byref(TotalNumberOfBytes), TotalNumberOfFreeBytes
    )
    return _usagetuple(
        TotalNumberOfBytes.value,
        TotalNumberOfBytes.value - FreeBytesAvailableToCaller.value,
        FreeBytesAvailableToCaller.value,
    )


def _volume_info_windows(path: str) -> _volumeinfotuple:
    if not path.endswith("\\"):
        raise ValueError("X: usually doesn't work. X:\\ does.")

    RootPathName = LPCWSTR(path)
    VolumeNameBuffer = create_unicode_buffer(MAX_PATH + 1)
    VolumeNameSize = MAX_PATH + 1
    VolumeSerialNumber = DWORD()
    MaximumComponentLength = DWORD()
    FileSystemFlags = DWORD()
    FileSystemNameBuffer = create_unicode_buffer(MAX_PATH + 1)
    FileSystemNameSize = MAX_PATH + 1

    fileapi.GetVolumeInformationW(
        RootPathName,
        VolumeNameBuffer,
        VolumeNameSize,
        byref(VolumeSerialNumber),
        byref(MaximumComponentLength),
        byref(FileSystemFlags),
        FileSystemNameBuffer,
        FileSystemNameSize,
    )

    return _volumeinfotuple(
        VolumeNameBuffer.value,
        VolumeSerialNumber.value,
        MaximumComponentLength.value,
        FileSystemFlags.value,
        FileSystemNameBuffer.value,
    )


def _interrupt_windows() -> None:
    os.kill(os.getpid(), signal.CTRL_C_EVENT)  # fixme: verify: works on win 10 but not on win 7


def _filemanager_cmd_windows(path: str) -> str:
    return f'explorer.exe /select,"{path}"'


if __name__ == "__main__":
    s = "\033[35m" + "color-test" + "\033[39m" + " test end"
    print(s)
    with EnableAnsi():
        print(s)
    print(s)
