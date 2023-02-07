from ctypes import FormatError, GetLastError, WinError, byref, sizeof
from ctypes.wintypes import DWORD, USHORT
from errno import EACCES

from cwinsdk.um.fileapi import INVALID_FILE_SIZE, CreateFileW, GetCompressedFileSizeW
from cwinsdk.um.handleapi import INVALID_HANDLE_VALUE
from cwinsdk.um.WinBase import GetFileInformationByHandleEx, OpenFileById
from cwinsdk.um.winioctl import FSCTL_SET_COMPRESSION
from cwinsdk.um.winnt import COMPRESSION_FORMAT_DEFAULT, COMPRESSION_FORMAT_NONE, FILE_SHARE_READ, FILE_SHARE_WRITE
from cwinsdk.windows import ERROR_SHARING_VIOLATION  # structs; enums
from cwinsdk.windows import (
    FILE_ID_DESCRIPTOR,
    FILE_ID_INFO,
    FILE_ID_TYPE,
    FILE_INFO_BY_HANDLE_CLASS,
    GENERIC_READ,
    OPEN_EXISTING,
)

from .device import EMPTY_BUFFER, MyDeviceIoControl
from .handle import WindowsHandle, _mode2access

NO_ERROR = 0


class SharingViolation(OSError):
    pass


def GetCompressedFileSize(path: str) -> int:
    HighPart = DWORD()
    LowPart = GetCompressedFileSizeW(path, byref(HighPart))

    if LowPart == INVALID_FILE_SIZE:
        if GetLastError() != NO_ERROR:
            e = WinError()
            e.filename = path
            raise e

    return (HighPart.value << 32) + LowPart


class WindowsFile(WindowsHandle):
    def __init__(self, handle: int) -> None:
        WindowsHandle.__init__(self, handle, doclose=True)

    @classmethod
    def from_path(cls, path: str, mode: str = "r", shared: bool = False) -> "WindowsFile":
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
                e = WinError()
                e.filename = path
                raise e

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

    def info(self) -> FILE_ID_INFO:
        FileInformation = FILE_ID_INFO()
        GetFileInformationByHandleEx(
            self.handle, FILE_INFO_BY_HANDLE_CLASS.FileIdInfo, byref(FileInformation), sizeof(FileInformation)
        )
        return FileInformation

    def set_compression(self, compressed: bool) -> None:
        if compressed:
            InBuffer = USHORT(COMPRESSION_FORMAT_DEFAULT)
        else:
            InBuffer = USHORT(COMPRESSION_FORMAT_NONE)
        MyDeviceIoControl(self.handle, FSCTL_SET_COMPRESSION, InBuffer, EMPTY_BUFFER())


def is_open_for_write(path: str) -> bool:
    """Tests if file is already open for write
    by trying to open it in exclusive read model.
    """

    try:
        with WindowsFile.from_path(path, mode="r", shared=False):
            return False
    except SharingViolation:
        return True


def set_compression(path: str, compressed: bool) -> None:
    with WindowsFile.from_path(path, mode="w+") as wf:
        wf.set_compression(compressed)


if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument("path")
    args = parser.parse_args()

    with WindowsFile.from_path(args.path, mode="r", shared=False) as wf:
        print("Volume serial number:", wf.info().VolumeSerialNumber)
        print("File id:", bytes(wf.info().FileId).hex())
