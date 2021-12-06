from __future__ import generator_stop

from ctypes import FormatError, GetLastError, WinError, byref, sizeof
from errno import EACCES

from cwinsdk.um.handleapi import INVALID_HANDLE_VALUE
from cwinsdk.um.winnt import FILE_SHARE_READ, FILE_SHARE_WRITE
from cwinsdk.windows import ERROR_SHARING_VIOLATION  # structs; enums
from cwinsdk.windows import (
    FILE_ID_DESCRIPTOR,
    FILE_ID_INFO,
    FILE_ID_TYPE,
    FILE_INFO_BY_HANDLE_CLASS,
    GENERIC_READ,
    OPEN_EXISTING,
    CreateFileW,
    GetFileInformationByHandleEx,
    OpenFileById,
)

from .handle import WindowsHandle, _mode2access


class SharingViolation(OSError):
    pass


class WindowsFile(WindowsHandle):
    def __init__(self, handle):
        # type: (int, ) -> None

        WindowsHandle.__init__(self, handle, doclose=True)

    @classmethod
    def from_path(cls, path, mode="r", shared=False):
        # type: (str, str, bool) -> WindowsFile

        """Create a Windows file objects from `path`.
        If shared is False: allow write access from other processes.
        """

        DesiredAccess = _mode2access[mode]

        if shared:
            ShareMode = FILE_SHARE_READ | FILE_SHARE_WRITE
        else:
            ShareMode = FILE_SHARE_READ

        SecurityAttributes = None
        CreationDisposition = OPEN_EXISTING
        FlagsAndAttributes = 0

        handle = CreateFileW(
            path, DesiredAccess, ShareMode, SecurityAttributes, CreationDisposition, FlagsAndAttributes, None
        )

        if handle == INVALID_HANDLE_VALUE:
            winerror = GetLastError()
            if winerror == ERROR_SHARING_VIOLATION:
                errno = EACCES
                strerror = FormatError(winerror)
                raise SharingViolation(errno, strerror, path, winerror)
            else:
                raise WinError()

        return cls(handle)

    @classmethod
    def from_fileid(cls, volume, fileid):
        VolumeHint = None  # open volume handle here
        FileId = FILE_ID_DESCRIPTOR(Size=..., Type=FILE_ID_TYPE.ExtendedFileIdType)
        DesiredAccess = GENERIC_READ
        ShareMode = FILE_SHARE_READ | FILE_SHARE_WRITE
        lpSecurityAttributes = None
        FlagsAndAttributes = 0

        handle = OpenFileById(
            VolumeHint, byref(FileId), DesiredAccess, ShareMode, lpSecurityAttributes, FlagsAndAttributes
        )
        return cls(handle)

    def info(self):
        FileInformation = FILE_ID_INFO()
        GetFileInformationByHandleEx(
            self.handle, FILE_INFO_BY_HANDLE_CLASS.FileIdInfo, byref(FileInformation), sizeof(FileInformation)
        )
        return FileInformation


def is_open_for_write(path):
    # type: (str, ) -> bool

    """Tests if file is already open for write
    by trying to open it in exclusive read model.
    """

    try:
        with WindowsFile.from_path(path, mode="r", shared=False):
            return False
    except SharingViolation:
        return True


if __name__ == "__main__":

    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument("path")
    args = parser.parse_args()

    with WindowsFile.from_path(args.path, mode="r", shared=False) as wf:
        print("Volume serial number:", wf.info().VolumeSerialNumber)
        print("File id:", bytes(wf.info().FileId).hex())
