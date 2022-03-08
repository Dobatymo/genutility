from __future__ import generator_stop

import sys

if sys.platform != "win32":
    raise ImportError("win submodule is only available on Windows")

import re
from ctypes import Structure, WinError, byref, create_unicode_buffer, sizeof
from ctypes.wintypes import BYTE, DWORD
from typing import TYPE_CHECKING

from cwinsdk import struct2dict
from cwinsdk.um.fileapi import OPEN_EXISTING, CreateFileW
from cwinsdk.um.handleapi import INVALID_HANDLE_VALUE, CloseHandle
from cwinsdk.um.ioapiset import DeviceIoControl
from cwinsdk.um.winioctl import (
    DISK_GEOMETRY,
    FSCTL_ALLOW_EXTENDED_DASD_IO,
    FSCTL_LOCK_VOLUME,
    FSCTL_UNLOCK_VOLUME,
    GET_LENGTH_INFORMATION,
    GETVERSIONINPARAMS,
    IOCTL_DISK_GET_DRIVE_GEOMETRY,
    IOCTL_DISK_GET_LENGTH_INFO,
    IOCTL_DISK_VERIFY,
    IOCTL_STORAGE_QUERY_PROPERTY,
    IOCTL_STORAGE_READ_CAPACITY,
    PARTITION_IFS,
    PARTITION_MSFT_RECOVERY,
    SMART_GET_VERSION,
    STORAGE_ACCESS_ALIGNMENT_DESCRIPTOR,
    STORAGE_DEVICE_DESCRIPTOR,
    STORAGE_PROPERTY_ID,
    STORAGE_PROPERTY_QUERY,
    STORAGE_QUERY_TYPE,
    STORAGE_READ_CAPACITY,
    VERIFY_INFORMATION,
)
from cwinsdk.um.winnt import FILE_SHARE_READ, FILE_SHARE_WRITE

from ..exceptions import assert_true
from .handle import WindowsHandle, _mode2access

if TYPE_CHECKING:
    from typing import Any


class EMPTY_BUFFER(Structure):
    pass


def get_length(path):
    # type: (str, ) -> int

    """Returns for:
    partitions: the full partition size (might be larger than disk_usage().total)
    drives: the full drive size (might be larger than the one computed from the drive geometry)
    """

    handle = open_device(path)
    try:
        InBuffer = EMPTY_BUFFER()
        OutBuffer = GET_LENGTH_INFORMATION()
        MyDeviceIoControl(handle, IOCTL_DISK_GET_LENGTH_INFO, InBuffer, OutBuffer)

        return OutBuffer.Length

    finally:
        CloseHandle(handle)


class Volume(WindowsHandle):
    def __init__(self, path):
        # type: (str, ) -> None

        handle = open_logical_volume(path)
        WindowsHandle.__init__(self, handle)

    def lock(self):
        MyDeviceIoControl(self.handle, FSCTL_LOCK_VOLUME, EMPTY_BUFFER(), EMPTY_BUFFER())

    def unlock(self):
        MyDeviceIoControl(self.handle, FSCTL_UNLOCK_VOLUME, EMPTY_BUFFER(), EMPTY_BUFFER())

    def extend(self):
        MyDeviceIoControl(self.handle, FSCTL_ALLOW_EXTENDED_DASD_IO, EMPTY_BUFFER(), EMPTY_BUFFER())


class Drive(WindowsHandle):
    def __init__(self, DriveIndex):
        # type: (int, ) -> None

        handle = open_physical_drive(DriveIndex)
        WindowsHandle.__init__(self, handle)

    def get_alignment(self):
        # type: () -> dict

        InBuffer = STORAGE_PROPERTY_QUERY()
        OutBuffer = STORAGE_ACCESS_ALIGNMENT_DESCRIPTOR()

        InBuffer.PropertyId = STORAGE_PROPERTY_ID.StorageAccessAlignmentProperty
        InBuffer.QueryType = STORAGE_QUERY_TYPE.PropertyStandardQuery

        MyDeviceIoControl(self.handle, IOCTL_STORAGE_QUERY_PROPERTY, InBuffer, OutBuffer)

        return struct2dict(OutBuffer)

    def get_capacity(self):
        # type: () -> dict

        """Accept drive and volume handles, but always returns related drive information.
        The DiskLength returned is the same as if `get_length` is used on the related drive.
        """

        InBuffer = EMPTY_BUFFER()
        OutBuffer = STORAGE_READ_CAPACITY()
        MyDeviceIoControl(self.handle, IOCTL_STORAGE_READ_CAPACITY, InBuffer, OutBuffer)

        return struct2dict(OutBuffer)

    # was: StorageQuery
    def get_device(self):
        # type: () -> dict

        InBuffer = STORAGE_PROPERTY_QUERY()
        OutBuffer = STORAGE_DEVICE_DESCRIPTOR()

        InBuffer.PropertyId = STORAGE_PROPERTY_ID.StorageDeviceProperty
        InBuffer.QueryType = STORAGE_QUERY_TYPE.PropertyStandardQuery
        InBuffer.AdditionalParameters = (BYTE * 1)(0)

        MyDeviceIoControl(self.handle, IOCTL_STORAGE_QUERY_PROPERTY, InBuffer, OutBuffer)

        return struct2dict(OutBuffer)

    def get_geometry(self):

        InBuffer = EMPTY_BUFFER()
        OutBuffer = DISK_GEOMETRY()
        MyDeviceIoControl(self.handle, IOCTL_DISK_GET_DRIVE_GEOMETRY, InBuffer, OutBuffer)

        return struct2dict(OutBuffer)

    def get_smart_version(self):
        # type: () -> dict

        InBuffer = EMPTY_BUFFER()
        OutBuffer = GETVERSIONINPARAMS()

        MyDeviceIoControl(self.handle, SMART_GET_VERSION, InBuffer, OutBuffer)

        return struct2dict(OutBuffer)

    def verify_extent(self, start, length):
        # type: (int, int) -> None

        """Can cause issues with some drivers (like TrueCrypt)."""

        InBuffer = VERIFY_INFORMATION()
        OutBuffer = EMPTY_BUFFER()

        InBuffer.StartingOffset = start
        InBuffer.Length = length

        MyDeviceIoControl(self.handle, IOCTL_DISK_VERIFY, InBuffer, OutBuffer)


def get_drive_size(DriveIndex):
    with Drive(DriveIndex) as drive:
        geo = drive.get_geometry()
    return geo["Cylinders"] * geo["TracksPerCylinder"] * geo["SectorsPerTrack"] * geo["BytesPerSector"]


def partition_style_string(partition_style):
    return {0: "MBR", 1: "GPT"}.get(partition_style, "Unknown")


def partition_type_string(partition_type):
    return {PARTITION_IFS: "NTFS/exFAT", PARTITION_MSFT_RECOVERY: "Recovery"}.get(partition_type, "Unknown")


def MyDeviceIoControl(DeviceHandle, IoControlCode, InBuffer, OutBuffer, check_output=True):
    # type: (Any, Any, Any, Any, bool) -> None

    BytesReturned = DWORD()

    assert_true("IoControlCode", IoControlCode)

    ret = DeviceIoControl(
        DeviceHandle,
        IoControlCode,
        byref(InBuffer),
        sizeof(InBuffer),
        byref(OutBuffer),
        sizeof(OutBuffer),
        byref(BytesReturned),
        None,
    )

    if ret == 0:
        raise WinError()

    if check_output and BytesReturned.value != sizeof(OutBuffer):
        raise RuntimeError(f"DeviceIoControl expected {sizeof(OutBuffer)} bytes but got {BytesReturned.value} bytes")


def open_device(FileName, mode="r"):

    DesiredAccess = _mode2access[mode]

    DeviceHandle = CreateFileW(
        FileName, DesiredAccess, FILE_SHARE_READ | FILE_SHARE_WRITE, None, OPEN_EXISTING, 0, None
    )

    if DeviceHandle == INVALID_HANDLE_VALUE:
        raise WinError()

    return DeviceHandle


volumep = re.compile(r"^\\\\[\.\?]\\[A-Z]:$")
drivep = re.compile(r"^\\\\[\.\?]\\PHYSICALDRIVE[0-9]$")


def is_volume_or_drive(s):

    from argparse import ArgumentTypeError

    pre = "\\\\.\\"
    if not s.startswith(pre):
        s = pre + s

    s = s.upper()

    if volumep.match(s) or drivep.match(s):
        return s
    else:
        raise ArgumentTypeError("X: or PHYSICALDRIVEX")


def open_logical_volume(FileName):
    assert volumep.match(FileName)
    return open_device(FileName)


def open_physical_drive(DriveIndex):
    # type: (int, ) -> Any

    assert isinstance(DriveIndex, int)
    drive = rf"\\.\PHYSICALDRIVE{DriveIndex}"
    FileName = create_unicode_buffer(drive)

    return open_device(FileName)


if __name__ == "__main__":

    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument("driveindex", type=int)
    args = parser.parse_args()

    with Drive(args.driveindex) as d:
        print("Alignment:", d.get_alignment())
        print("Capacity:", d.get_capacity())
        print("Device:", d.get_device())
        print("Geometry:", d.get_geometry())
        try:
            print("SMART version:", d.get_smart_version())
        except OSError as e:
            print(e)
