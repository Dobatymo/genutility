from ctypes import byref, create_unicode_buffer, sizeof
from ctypes.wintypes import DWORD, LARGE_INTEGER
from enum import IntFlag
from msvcrt import get_osfhandle, open_osfhandle
from os import fdopen
from typing import Optional

from cwinsdk import struct2dict
from cwinsdk.km import ntddk, ntifs, wdm
from cwinsdk.shared.minwindef import MAX_PATH
from cwinsdk.um import fileapi, winnt
from cwinsdk.um.handleapi import CloseHandle
from cwinsdk.um.winnt import GENERIC_READ, GENERIC_WRITE
from typing_extensions import Self

_mode2access = {"": 0, "r": GENERIC_READ, "w": GENERIC_WRITE, "r+": GENERIC_READ | GENERIC_WRITE}


class FileSystem(IntFlag):
    CASE_SENSITIVE_SEARCH = winnt.FILE_CASE_SENSITIVE_SEARCH
    CASE_PRESERVED_NAMES = winnt.FILE_CASE_PRESERVED_NAMES
    UNICODE_ON_DISK = winnt.FILE_UNICODE_ON_DISK
    PERSISTENT_ACLS = winnt.FILE_PERSISTENT_ACLS
    FILE_COMPRESSION = winnt.FILE_FILE_COMPRESSION
    VOLUME_QUOTAS = winnt.FILE_VOLUME_QUOTAS
    SUPPORTS_SPARSE_FILES = winnt.FILE_SUPPORTS_SPARSE_FILES
    SUPPORTS_REPARSE_POINTS = winnt.FILE_SUPPORTS_REPARSE_POINTS
    SUPPORTS_REMOTE_STORAGE = winnt.FILE_SUPPORTS_REMOTE_STORAGE
    RETURNS_CLEANUP_RESULT_INFO = winnt.FILE_RETURNS_CLEANUP_RESULT_INFO
    SUPPORTS_POSIX_UNLINK_RENAME = winnt.FILE_SUPPORTS_POSIX_UNLINK_RENAME
    VOLUME_IS_COMPRESSED = winnt.FILE_VOLUME_IS_COMPRESSED
    SUPPORTS_OBJECT_IDS = winnt.FILE_SUPPORTS_OBJECT_IDS
    SUPPORTS_ENCRYPTION = winnt.FILE_SUPPORTS_ENCRYPTION
    NAMED_STREAMS = winnt.FILE_NAMED_STREAMS
    READ_ONLY_VOLUME = winnt.FILE_READ_ONLY_VOLUME
    SEQUENTIAL_WRITE_ONCE = winnt.FILE_SEQUENTIAL_WRITE_ONCE
    SUPPORTS_TRANSACTIONS = winnt.FILE_SUPPORTS_TRANSACTIONS
    SUPPORTS_HARD_LINKS = winnt.FILE_SUPPORTS_HARD_LINKS
    SUPPORTS_EXTENDED_ATTRIBUTES = winnt.FILE_SUPPORTS_EXTENDED_ATTRIBUTES
    SUPPORTS_OPEN_BY_FILE_ID = winnt.FILE_SUPPORTS_OPEN_BY_FILE_ID
    SUPPORTS_USN_JOURNAL = winnt.FILE_SUPPORTS_USN_JOURNAL
    SUPPORTS_INTEGRITY_STREAMS = winnt.FILE_SUPPORTS_INTEGRITY_STREAMS
    SUPPORTS_BLOCK_REFCOUNTING = winnt.FILE_SUPPORTS_BLOCK_REFCOUNTING
    SUPPORTS_SPARSE_VDL = winnt.FILE_SUPPORTS_SPARSE_VDL
    DAX_VOLUME = winnt.FILE_DAX_VOLUME
    SUPPORTS_GHOSTING = winnt.FILE_SUPPORTS_GHOSTING


class WindowsHandle:
    def __init__(self, handle: int, doclose: bool = True, timeout_ms: Optional[int] = None) -> None:
        if not isinstance(handle, int):
            raise TypeError("handle must be an int")

        self.handle = handle
        self.doclose = doclose
        self.timeout_ms = timeout_ms

    @property
    def overlapped(self) -> True:
        return self.timeout_ms is not None

    @classmethod
    def from_file(cls, fp):
        return cls.from_fd(fp.fileno())

    @classmethod
    def from_fd(cls, fd):
        return cls(get_osfhandle(fd), doclose=False)

    def get_fd(self, flags):
        return open_osfhandle(self.handle, flags)

    def get_file(self, flags, mode="r", buffering=-1, encoding=None, errors=None, newline=None, closefd=True):
        return fdopen(self.get_fd(flags), mode, buffering, encoding, errors, newline, closefd)

    def close(self) -> None:
        CloseHandle(self.handle)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.doclose:
            self.close()

    def filesize(self) -> int:
        FileSize = LARGE_INTEGER()
        fileapi.GetFileSizeEx(self.handle, byref(FileSize))
        return FileSize

    def file_information(self) -> dict:
        FileInformation = fileapi.BY_HANDLE_FILE_INFORMATION()
        fileapi.GetFileInformationByHandle(self.handle, byref(FileInformation))
        return struct2dict(FileInformation)

    def volume_information(self) -> dict:
        VolumeNameBuffer = create_unicode_buffer(MAX_PATH + 1)
        VolumeNameSize = MAX_PATH + 1
        VolumeSerialNumber = DWORD()
        MaximumComponentLength = DWORD()
        FileSystemFlags = DWORD()
        FileSystemNameBuffer = create_unicode_buffer(MAX_PATH + 1)
        FileSystemNameSize = MAX_PATH + 1

        fileapi.GetVolumeInformationByHandleW(
            self.handle,
            VolumeNameBuffer,
            VolumeNameSize,
            byref(VolumeSerialNumber),
            byref(MaximumComponentLength),
            byref(FileSystemFlags),
            FileSystemNameBuffer,
            FileSystemNameSize,
        )

        return {
            "VolumeName": VolumeNameBuffer.value,
            "VolumeSerialNumber": VolumeSerialNumber.value,
            "MaximumComponentLength": MaximumComponentLength.value,
            "FileSystemFlags": FileSystem(FileSystemFlags.value),
            "FileSystemName": FileSystemNameBuffer.value,
        }

    def fs_full_size(self) -> dict:
        IoStatusBlock = wdm.IO_STATUS_BLOCK()
        FsInformation = ntddk.FILE_FS_FULL_SIZE_INFORMATION()

        ntifs.NtQueryVolumeInformationFile(
            self.handle,
            byref(IoStatusBlock),
            byref(FsInformation),
            sizeof(ntddk.FILE_FS_FULL_SIZE_INFORMATION),
            wdm.FS_INFORMATION_CLASS.FileFsFullSizeInformation,
        )
        return struct2dict(FsInformation)
