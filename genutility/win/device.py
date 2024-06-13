import sys

if sys.platform != "win32":
    raise ImportError("win submodule is only available on Windows")

import logging
import os
import re
from argparse import ArgumentTypeError
from ctypes import POINTER, Structure, addressof, byref, cast, create_unicode_buffer, sizeof, string_at
from ctypes.wintypes import BYTE, DWORD, HANDLE, PBYTE, ULONG
from enum import Enum, IntEnum, IntFlag
from textwrap import indent
from typing import Any, Iterator, List, Optional, Tuple, Union

from cwinsdk import struct2dict
from cwinsdk.shared import devpkey, devpropdef, diskguid, ntddscsi, ntddstor, nvme, scsi, srb, winerror
from cwinsdk.shared.basetsd import UINT32
from cwinsdk.shared.guiddef import GUID
from cwinsdk.um import setupapi, winioctl
from cwinsdk.um.fileapi import (
    OPEN_EXISTING,
    CreateFileW,
    FindFirstVolumeW,
    FindNextVolumeW,
    FindVolumeClose,
    GetLogicalDriveStringsW,
    GetVolumeNameForVolumeMountPointW,
    GetVolumePathNamesForVolumeNameW,
    QueryDosDeviceW,
)
from cwinsdk.um.handleapi import CloseHandle
from cwinsdk.um.ioapiset import CancelIo, DeviceIoControl, GetOverlappedResultEx
from cwinsdk.um.minwinbase import OVERLAPPED
from cwinsdk.um.synchapi import CreateEventW
from cwinsdk.um.winbase import (
    FILE_FLAG_OVERLAPPED,
    FindFirstVolumeMountPointW,
    FindNextVolumeMountPointW,
    FindVolumeMountPointClose,
)
from cwinsdk.um.winnt import FILE_SHARE_READ, FILE_SHARE_WRITE
from typing_extensions import Self

from ..exceptions import assert_true
from .handle import WindowsHandle, _mode2access

assert sizeof(winioctl.STORAGE_PROTOCOL_SPECIFIC_DATA) == 40

logger = logging.getLogger(__name__)

win32_drive_letter_p = re.compile(r"^\\\\[\.\?]\\[A-Z]:$", flags=re.IGNORECASE)
physical_drive_p = re.compile(r"^\\\\[\.\?]\\PHYSICALDRIVE[0-9]+$")
volume_guid_path_p = re.compile(
    r"^\\\\\?\\Volume\{[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\}\\$", flags=re.IGNORECASE
)
logical_drive_p = re.compile(r"^[A-Z]:\\$", flags=re.IGNORECASE)


class SrbType(IntEnum):
    SCSI_REQUEST_BLOCK = srb.SRB_TYPE_SCSI_REQUEST_BLOCK
    STORAGE_REQUEST_BLOCK = srb.SRB_TYPE_STORAGE_REQUEST_BLOCK
    NVME_REQUEST_BLOCK = srb.SRB_TYPE_NVME_REQUEST_BLOCK


class IsDirtyFlags(IntFlag):
    VOLUME_IS_CLEAN = 0
    VOLUME_IS_DIRTY = winioctl.VOLUME_IS_DIRTY
    VOLUME_UPGRADE_SCHEDULED = winioctl.VOLUME_UPGRADE_SCHEDULED
    VOLUME_SESSION_OPEN = winioctl.VOLUME_SESSION_OPEN


class StorageAddressType(IntEnum):
    BTL8 = srb.STORAGE_ADDRESS_TYPE_BTL8
    NVME = srb.STORAGE_ADDRESS_TYPE_NVME


class ScsiDriveType(IntEnum):
    DIRECT_ACCESS_DEVICE = scsi.DIRECT_ACCESS_DEVICE
    SEQUENTIAL_ACCESS_DEVICE = scsi.SEQUENTIAL_ACCESS_DEVICE
    PRINTER_DEVICE = scsi.PRINTER_DEVICE
    PROCESSOR_DEVICE = scsi.PROCESSOR_DEVICE
    WRITE_ONCE_READ_MULTIPLE_DEVICE = scsi.WRITE_ONCE_READ_MULTIPLE_DEVICE
    READ_ONLY_DIRECT_ACCESS_DEVICE = scsi.READ_ONLY_DIRECT_ACCESS_DEVICE
    SCANNER_DEVICE = scsi.SCANNER_DEVICE
    OPTICAL_DEVICE = scsi.OPTICAL_DEVICE
    MEDIUM_CHANGER = scsi.MEDIUM_CHANGER
    COMMUNICATION_DEVICE = scsi.COMMUNICATION_DEVICE
    ARRAY_CONTROLLER_DEVICE = scsi.ARRAY_CONTROLLER_DEVICE
    SCSI_ENCLOSURE_DEVICE = scsi.SCSI_ENCLOSURE_DEVICE
    REDUCED_BLOCK_DEVICE = scsi.REDUCED_BLOCK_DEVICE
    OPTICAL_CARD_READER_WRITER_DEVICE = scsi.OPTICAL_CARD_READER_WRITER_DEVICE
    BRIDGE_CONTROLLER_DEVICE = scsi.BRIDGE_CONTROLLER_DEVICE
    OBJECT_BASED_STORAGE_DEVICE = scsi.OBJECT_BASED_STORAGE_DEVICE
    HOST_MANAGED_ZONED_BLOCK_DEVICE = scsi.HOST_MANAGED_ZONED_BLOCK_DEVICE
    UNKNOWN_OR_NO_DEVICE = scsi.UNKNOWN_OR_NO_DEVICE
    LOGICAL_UNIT_NOT_PRESENT_DEVICE = scsi.LOGICAL_UNIT_NOT_PRESENT_DEVICE


class FILESYSTEM_STATISTICS_TYPE(IntEnum):
    NTFS = winioctl.FILESYSTEM_STATISTICS_TYPE_NTFS
    FAT = winioctl.FILESYSTEM_STATISTICS_TYPE_FAT
    EXFAT = winioctl.FILESYSTEM_STATISTICS_TYPE_EXFAT
    REFS = winioctl.FILESYSTEM_STATISTICS_TYPE_REFS


class PartitionInt(IntEnum):
    ENTRY_UNUSED = winioctl.PARTITION_ENTRY_UNUSED
    IFS = winioctl.PARTITION_IFS
    FAT32 = winioctl.PARTITION_FAT32
    MSFT_RECOVERY = winioctl.PARTITION_MSFT_RECOVERY


class PartitionGuid(Enum):
    BASIC_DATA = diskguid.PARTITION_BASIC_DATA_GUID
    BSP = diskguid.PARTITION_BSP_GUID
    CLUSTER = diskguid.PARTITION_CLUSTER_GUID
    DPP = diskguid.PARTITION_DPP_GUID
    ENTRY_UNUSED = diskguid.PARTITION_ENTRY_UNUSED_GUID
    LDM_DATA = diskguid.PARTITION_LDM_DATA_GUID
    LDM_METADATA = diskguid.PARTITION_LDM_METADATA_GUID
    LEGACY_BL = diskguid.PARTITION_LEGACY_BL_GUID
    LEGACY_BL_BACKUP = diskguid.PARTITION_LEGACY_BL_GUID_BACKUP
    MAIN_OS = diskguid.PARTITION_MAIN_OS_GUID
    MSFT_RECOVERY = diskguid.PARTITION_MSFT_RECOVERY_GUID
    MSFT_RESERVED = diskguid.PARTITION_MSFT_RESERVED_GUID
    MSFT_SNAPSHOT = diskguid.PARTITION_MSFT_SNAPSHOT_GUID
    OS_DATA = diskguid.PARTITION_OS_DATA_GUID
    PATCH = diskguid.PARTITION_PATCH_GUID
    PRE_INSTALLED = diskguid.PARTITION_PRE_INSTALLED_GUID
    SBL_CACHE_SSD = diskguid.PARTITION_SBL_CACHE_SSD_GUID
    SBL_CACHE_SSD_RESERVED = diskguid.PARTITION_SBL_CACHE_SSD_RESERVED_GUID
    SBL_CACHE_HDD = diskguid.PARTITION_SBL_CACHE_HDD_GUID
    SERVICING_FILES = diskguid.PARTITION_SERVICING_FILES_GUID
    SERVICING_METADATA = diskguid.PARTITION_SERVICING_METADATA_GUID
    SERVICING_RESERVE = diskguid.PARTITION_SERVICING_RESERVE_GUID
    SERVICING_STAGING_ROOT = diskguid.PARTITION_SERVICING_STAGING_ROOT_GUID
    SPACES = diskguid.PARTITION_SPACES_GUID
    SPACES_DATA = diskguid.PARTITION_SPACES_DATA_GUID
    SYSTEM = diskguid.PARTITION_SYSTEM_GUID
    WINDOWS_SYSTEM = diskguid.PARTITION_WINDOWS_SYSTEM_GUID


class DEVICE_TYPE(IntEnum):
    BEEP = winioctl.FILE_DEVICE_BEEP
    CD_ROM = winioctl.FILE_DEVICE_CD_ROM
    CD_ROM_FILE_SYSTEM = winioctl.FILE_DEVICE_CD_ROM_FILE_SYSTEM
    CONTROLLER = winioctl.FILE_DEVICE_CONTROLLER
    DATALINK = winioctl.FILE_DEVICE_DATALINK
    DFS = winioctl.FILE_DEVICE_DFS
    DISK = winioctl.FILE_DEVICE_DISK
    DISK_FILE_SYSTEM = winioctl.FILE_DEVICE_DISK_FILE_SYSTEM
    FILE_SYSTEM = winioctl.FILE_DEVICE_FILE_SYSTEM
    INPORT_PORT = winioctl.FILE_DEVICE_INPORT_PORT
    KEYBOARD = winioctl.FILE_DEVICE_KEYBOARD
    MAILSLOT = winioctl.FILE_DEVICE_MAILSLOT
    MIDI_IN = winioctl.FILE_DEVICE_MIDI_IN
    MIDI_OUT = winioctl.FILE_DEVICE_MIDI_OUT
    MOUSE = winioctl.FILE_DEVICE_MOUSE
    MULTI_UNC_PROVIDER = winioctl.FILE_DEVICE_MULTI_UNC_PROVIDER
    NAMED_PIPE = winioctl.FILE_DEVICE_NAMED_PIPE
    NETWORK = winioctl.FILE_DEVICE_NETWORK
    NETWORK_BROWSER = winioctl.FILE_DEVICE_NETWORK_BROWSER
    NETWORK_FILE_SYSTEM = winioctl.FILE_DEVICE_NETWORK_FILE_SYSTEM
    NULL = winioctl.FILE_DEVICE_NULL
    PARALLEL_PORT = winioctl.FILE_DEVICE_PARALLEL_PORT
    PHYSICAL_NETCARD = winioctl.FILE_DEVICE_PHYSICAL_NETCARD
    PRINTER = winioctl.FILE_DEVICE_PRINTER
    SCANNER = winioctl.FILE_DEVICE_SCANNER
    SERIAL_MOUSE_PORT = winioctl.FILE_DEVICE_SERIAL_MOUSE_PORT
    SERIAL_PORT = winioctl.FILE_DEVICE_SERIAL_PORT
    SCREEN = winioctl.FILE_DEVICE_SCREEN
    SOUND = winioctl.FILE_DEVICE_SOUND
    STREAMS = winioctl.FILE_DEVICE_STREAMS
    TAPE = winioctl.FILE_DEVICE_TAPE
    TAPE_FILE_SYSTEM = winioctl.FILE_DEVICE_TAPE_FILE_SYSTEM
    TRANSPORT = winioctl.FILE_DEVICE_TRANSPORT
    UNKNOWN = winioctl.FILE_DEVICE_UNKNOWN
    VIDEO = winioctl.FILE_DEVICE_VIDEO
    VIRTUAL_DISK = winioctl.FILE_DEVICE_VIRTUAL_DISK
    WAVE_IN = winioctl.FILE_DEVICE_WAVE_IN
    WAVE_OUT = winioctl.FILE_DEVICE_WAVE_OUT
    FILE_DEVICE_8042_PORT = 0x00000027
    NETWORK_REDIRECTOR = winioctl.FILE_DEVICE_NETWORK_REDIRECTOR
    BATTERY = winioctl.FILE_DEVICE_BATTERY
    BUS_EXTENDER = winioctl.FILE_DEVICE_BUS_EXTENDER
    MODEM = winioctl.FILE_DEVICE_MODEM
    VDM = winioctl.FILE_DEVICE_VDM
    MASS_STORAGE = winioctl.FILE_DEVICE_MASS_STORAGE
    SMB = winioctl.FILE_DEVICE_SMB
    KS = winioctl.FILE_DEVICE_KS
    CHANGER = winioctl.FILE_DEVICE_CHANGER
    SMARTCARD = winioctl.FILE_DEVICE_SMARTCARD
    ACPI = winioctl.FILE_DEVICE_ACPI
    DVD = winioctl.FILE_DEVICE_DVD
    FULLSCREEN_VIDEO = winioctl.FILE_DEVICE_FULLSCREEN_VIDEO
    DFS_FILE_SYSTEM = winioctl.FILE_DEVICE_DFS_FILE_SYSTEM
    DFS_VOLUME = winioctl.FILE_DEVICE_DFS_VOLUME
    SERENUM = winioctl.FILE_DEVICE_SERENUM
    TERMSRV = winioctl.FILE_DEVICE_TERMSRV
    KSEC = winioctl.FILE_DEVICE_KSEC
    FIPS = winioctl.FILE_DEVICE_FIPS
    INFINIBAND = winioctl.FILE_DEVICE_INFINIBAND
    VMBUS = winioctl.FILE_DEVICE_VMBUS
    CRYPT_PROVIDER = winioctl.FILE_DEVICE_CRYPT_PROVIDER
    WPD = winioctl.FILE_DEVICE_WPD
    BLUETOOTH = winioctl.FILE_DEVICE_BLUETOOTH
    MT_COMPOSITE = winioctl.FILE_DEVICE_MT_COMPOSITE
    MT_TRANSPORT = winioctl.FILE_DEVICE_MT_TRANSPORT
    BIOMETRIC = winioctl.FILE_DEVICE_BIOMETRIC
    PMI = winioctl.FILE_DEVICE_PMI
    EHSTOR = winioctl.FILE_DEVICE_EHSTOR
    DEVAPI = winioctl.FILE_DEVICE_DEVAPI
    GPIO = winioctl.FILE_DEVICE_GPIO
    USBEX = winioctl.FILE_DEVICE_USBEX
    CONSOLE = winioctl.FILE_DEVICE_CONSOLE
    NFP = winioctl.FILE_DEVICE_NFP
    SYSENV = winioctl.FILE_DEVICE_SYSENV
    VIRTUAL_BLOCK = winioctl.FILE_DEVICE_VIRTUAL_BLOCK
    POINT_OF_SERVICE = winioctl.FILE_DEVICE_POINT_OF_SERVICE
    STORAGE_REPLICATION = winioctl.FILE_DEVICE_STORAGE_REPLICATION
    TRUST_ENV = winioctl.FILE_DEVICE_TRUST_ENV
    UCM = winioctl.FILE_DEVICE_UCM
    UCMTCPCI = winioctl.FILE_DEVICE_UCMTCPCI
    PERSISTENT_MEMORY = winioctl.FILE_DEVICE_PERSISTENT_MEMORY
    NVDIMM = winioctl.FILE_DEVICE_NVDIMM
    HOLOGRAPHIC = winioctl.FILE_DEVICE_HOLOGRAPHIC
    SDFXHCI = winioctl.FILE_DEVICE_SDFXHCI
    UCMUCSI = winioctl.FILE_DEVICE_UCMUCSI


def is_volume_guid_path(s: str) -> bool:
    return volume_guid_path_p.match(s) is not None


def is_volume_guid_path_arg(s: str) -> str:
    if is_volume_guid_path(s):
        return s
    raise ArgumentTypeError("\\\\?\\Volume{GUID}\\")


def is_logical_drive(s: str) -> bool:
    return logical_drive_p.match(s) is not None


def is_logical_drive_arg(s: str) -> str:
    if is_logical_drive(s):
        return s
    raise ArgumentTypeError("X:\\")


def is_physical_drive(s: str) -> bool:
    return physical_drive_p.match(s) is not None


def is_physical_drive_arg(s: str) -> str:
    if is_physical_drive(s):
        return s
    raise ArgumentTypeError("\\\\?\\PHYSICALDRIVEX where X is a number")


def is_volume_or_drive_arg(s: str) -> str:
    pre = ("\\\\?\\", "\\\\.\\")
    if not s.startswith(pre):
        s = pre[0] + s

    s = s.upper()

    if is_volume_guid_path(s) or is_logical_drive(s) or is_physical_drive(s):
        return s
    else:
        raise ArgumentTypeError("X: or PHYSICALDRIVEX")


def logical_drive_to_win32_file_path(path: str) -> str:
    assert is_logical_drive(path)
    return rf"\\?\{path}"[:-1]


def logical_drive_to_win32_device_path(path: str) -> str:
    assert is_logical_drive(path)
    return rf"\\.\{path}"[:-1]


class EMPTY_BUFFER(Structure):
    pass


def struct_to_array(struct, array):
    tmp = string_at(addressof(struct), sizeof(struct))
    return array(*tmp)


def cstring(buffer: bytes, offset: int = 0, encoding="ascii") -> str:
    end = buffer.find(b"\0", offset)
    return buffer[offset:end].decode(encoding)


def mybyref(value: Optional[Structure]):
    if value is None:
        return None
    return byref(value)


def MyDeviceIoControl(
    DeviceHandle: Any,
    IoControlCode: Any,
    InBuffer: Any,
    OutBuffer: Any,
    *,
    timeout_ms: Optional[int] = None,
    check_output: bool = True,
) -> None:
    BytesReturned = DWORD()

    assert_true("IoControlCode", IoControlCode)

    logger.debug("DeviceIoControl, insize=%d, outsize=%d", sizeof(InBuffer), sizeof(OutBuffer))

    if timeout_ms is None:
        Overlapped = None
    else:
        Overlapped = OVERLAPPED()
        Overlapped.hEvent = CreateEventW(None, True, False, None)

    try:
        try:
            DeviceIoControl(
                DeviceHandle,
                IoControlCode,
                byref(InBuffer),
                sizeof(InBuffer),
                byref(OutBuffer),
                sizeof(OutBuffer),
                byref(BytesReturned),
                mybyref(Overlapped),
            )
        except OSError as e:
            if e.winerror != winerror.ERROR_IO_PENDING:
                raise

            try:
                NumberOfBytesTransferred = DWORD()
                bAlertable = True
                GetOverlappedResultEx(
                    DeviceHandle, byref(Overlapped), byref(NumberOfBytesTransferred), timeout_ms, bAlertable
                )
            except Exception:
                CancelIo(DeviceHandle)  # cancel I/O but don't wait to see if it's actually canceled
                raise

        if check_output and BytesReturned.value != sizeof(OutBuffer):
            raise RuntimeError(
                f"DeviceIoControl expected {sizeof(OutBuffer)} bytes but got {BytesReturned.value} bytes"
            )
    finally:
        if timeout_ms is not None:
            CloseHandle(Overlapped.hEvent)


def open_device(FileName, mode: str = "r", overlapped: bool = False) -> HANDLE:
    DesiredAccess = _mode2access[mode]

    if overlapped:
        FlagsAndAttributes = FILE_FLAG_OVERLAPPED
    else:
        FlagsAndAttributes = 0

    return CreateFileW(
        FileName, DesiredAccess, FILE_SHARE_READ | FILE_SHARE_WRITE, None, OPEN_EXISTING, FlagsAndAttributes, None
    )


def partition_info_to_json(p: winioctl.PARTITION_INFORMATION_EX) -> dict:
    if p.PartitionStyle == winioctl.PARTITION_STYLE.PARTITION_STYLE_MBR:  # MBR
        return {
            "PartitionStyle": p.PartitionStyle.to_enum(),
            "StartingOffset": p.StartingOffset,
            "PartitionLength": p.PartitionLength,
            "PartitionNumber": p.PartitionNumber,
            "RewritePartition": bool(p.RewritePartition.value),
            "IsServicePartition": bool(p.IsServicePartition.value),
            "PartitionType": PartitionInt(p.Mbr.PartitionType),
            "BootIndicator": bool(p.Mbr.BootIndicator.value),
            "RecognizedPartition": bool(p.Mbr.RecognizedPartition),
            "HiddenSectors": p.Mbr.HiddenSectors,
            "PartitionId": str(p.Mbr.PartitionId),
        }
    elif p.PartitionStyle == winioctl.PARTITION_STYLE.PARTITION_STYLE_GPT:  # GPT
        return {
            "PartitionStyle": p.PartitionStyle.to_enum(),
            "StartingOffset": p.StartingOffset,
            "PartitionLength": p.PartitionLength,
            "PartitionNumber": p.PartitionNumber,
            "RewritePartition": bool(p.RewritePartition.value),
            "IsServicePartition": bool(p.IsServicePartition.value),
            "PartitionType": PartitionGuid(p.Gpt.PartitionType),
            "PartitionId": str(p.Gpt.PartitionId),
            "Attributes": p.Gpt.Attributes,
            "Name": p.Gpt.Name,
        }
    else:
        return {}


def drive_layout_to_json(OutBuffer: winioctl.DRIVE_LAYOUT_INFORMATION_EX) -> dict:
    p_style = winioctl.PARTITION_STYLE(OutBuffer.PartitionStyle).to_enum()
    p_info = {"PartitionStyle": p_style}

    if p_style == winioctl.PARTITION_STYLE.PARTITION_STYLE_MBR:  # MBR
        p_info.update(struct2dict(OutBuffer.Mbr))
        p_info["PartitionEntry"] = []

        for p in OutBuffer.PartitionEntry:
            if p.Mbr.PartitionType == winioctl.PARTITION_ENTRY_UNUSED:
                continue

            p_info["PartitionEntry"].append(partition_info_to_json(p))
    elif p_style == winioctl.PARTITION_STYLE.PARTITION_STYLE_GPT:  # GPT
        p_info.update(struct2dict(OutBuffer.Gpt))
        p_info["PartitionEntry"] = []

        for p in OutBuffer.PartitionEntry:
            if p.Gpt.PartitionType == diskguid.PARTITION_ENTRY_UNUSED_GUID:
                continue

            p_info["PartitionEntry"].append(partition_info_to_json(p))

    return p_info


CREATE_FILE_SUPPORTED_PATHS = r"""Volumes:
  Logical drive
- \\?\C:
  Volume GUID path
- \\?\Volume{xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx}
  By disk and volume/partition id
- \\?\HarddiskVolume1
- \\?\CdRom0
- \\?\Harddisk0Partition1
- \\?\GLOBALROOT\Device\HarddiskVolume1
- \\?\GLOBALROOT\Device\Harddisk0\Partition1

Drives:
  By physical drive id
- \\?\PhysicalDrive0
  By physical drive id and DR#
- \\?\GLOBALROOT\Device\Harddisk0\DR0
  Physical device object name:
- \\?\GLOBALROOT\Device\00000001
  Device (interface) paths:
- \\?\usbstor#disk&...
- \\?\SCSI#Disk&...
- \\?\STORAGE#Volume#...
"""


def format_doc_string(**sub):
    def decorator(func):
        func.__doc__ = func.__doc__.format(**sub)
        return func

    return decorator


class StorageMixin:
    @classmethod
    @format_doc_string(CREATE_FILE_SUPPORTED_PATHS=indent(CREATE_FILE_SUPPORTED_PATHS, "        "))
    def from_raw_path(cls, path: str, mode: str = "r", timeout_ms: Optional[int] = None) -> Self:
        """
                Open using paths like

        {CREATE_FILE_SUPPORTED_PATHS}

                or any other path valid for `CreateFile`
        """

        overlapped = timeout_ms is not None
        return cls(open_device(path, mode, overlapped), timeout_ms=timeout_ms)

    # IOCTL_DISK

    def partition_info(self, asjson=True) -> Union[dict, winioctl.PARTITION_INFORMATION_EX]:
        """Returns for:
        - volumes: the information of the partition the volume is on
        - drives: the information for partition 0
            (which is not a valid partition, but has the same length information as the full disk)

        Same length value as from `length_info`.
        """

        InBuffer = EMPTY_BUFFER()
        OutBuffer = winioctl.PARTITION_INFORMATION_EX()
        MyDeviceIoControl(
            self.handle, winioctl.IOCTL_DISK_GET_PARTITION_INFO_EX, InBuffer, OutBuffer, timeout_ms=self.timeout_ms
        )
        if asjson:
            return partition_info_to_json(OutBuffer)
        else:
            return OutBuffer

    def drive_layout(self, max_partitions=128, asjson=True) -> Union[dict, winioctl.DRIVE_LAYOUT_INFORMATION_EX]:
        """Accepts drive and volume handles, but always returns related drive info."""

        InBuffer = EMPTY_BUFFER()
        OutBuffer = winioctl.DRIVE_LAYOUT_INFORMATION_EX_SIZE(max_partitions)()
        MyDeviceIoControl(self.handle, winioctl.IOCTL_DISK_GET_DRIVE_LAYOUT_EX, InBuffer, OutBuffer, check_output=False)
        if asjson:
            return drive_layout_to_json(OutBuffer)
        else:
            return OutBuffer

    def length_info(self) -> int:
        """Returns for:
        - volumes: the full partition size
            (might be larger than than the filesystem size ie. disk_usage().total)
        - drives: the full drive size
            (drive size might be different if computed from drive geometry,
            but the geometry is often incorrect)

        Requires read access rights.
        Same as length value in `partition_info`.
        """

        InBuffer = EMPTY_BUFFER()
        OutBuffer = winioctl.GET_LENGTH_INFORMATION()
        MyDeviceIoControl(
            self.handle, winioctl.IOCTL_DISK_GET_LENGTH_INFO, InBuffer, OutBuffer, timeout_ms=self.timeout_ms
        )
        return OutBuffer.Length

    def drive_geometry(self) -> dict:
        """Accepts drive and volume handles, but always returns related drive info."""

        InBuffer = EMPTY_BUFFER()
        OutBuffer = winioctl.DISK_GEOMETRY()
        MyDeviceIoControl(
            self.handle, winioctl.IOCTL_DISK_GET_DRIVE_GEOMETRY, InBuffer, OutBuffer, timeout_ms=self.timeout_ms
        )
        return struct2dict(OutBuffer)

    # IOCTL_STORAGE

    def storage_query_property(self, property_id: winioctl.STORAGE_PROPERTY_ID, asjson=True) -> Union[dict, Structure]:
        mapping = {
            winioctl.STORAGE_PROPERTY_ID.StorageAdapterProperty: winioctl.STORAGE_ADAPTER_DESCRIPTOR,
            winioctl.STORAGE_PROPERTY_ID.StorageAccessAlignmentProperty: winioctl.STORAGE_ACCESS_ALIGNMENT_DESCRIPTOR,
            winioctl.STORAGE_PROPERTY_ID.StorageDeviceSeekPenaltyProperty: winioctl.DEVICE_SEEK_PENALTY_DESCRIPTOR,
            winioctl.STORAGE_PROPERTY_ID.StorageDeviceTrimProperty: winioctl.DEVICE_TRIM_DESCRIPTOR,
            winioctl.STORAGE_PROPERTY_ID.StorageDeviceTemperatureProperty: winioctl.STORAGE_TEMPERATURE_DATA_DESCRIPTOR,
        }
        Descriptor = mapping[property_id]

        InBuffer = winioctl.STORAGE_PROPERTY_QUERY()
        OutBuffer = Descriptor()
        InBuffer.PropertyId = property_id
        InBuffer.QueryType = winioctl.STORAGE_QUERY_TYPE.PropertyStandardQuery
        MyDeviceIoControl(
            self.handle, winioctl.IOCTL_STORAGE_QUERY_PROPERTY, InBuffer, OutBuffer, timeout_ms=self.timeout_ms
        )
        if asjson:
            return struct2dict(OutBuffer)
        else:
            return OutBuffer

    def sqp_adapter(self) -> dict:
        """Accepts drive and volume handles, but always returns related drive info."""

        out = self.storage_query_property(winioctl.STORAGE_PROPERTY_ID.StorageAdapterProperty)
        out["BusType"] = ntddstor.STORAGE_BUS_TYPE(out["BusType"]).to_enum()
        out["SrbType"] = SrbType(out["SrbType"])
        out["AddressType"] = StorageAddressType(out["AddressType"])
        return out

    def sqp_alignment(self) -> dict:
        """Accepts drive and volume handles, but always returns related drive info."""

        return self.storage_query_property(winioctl.STORAGE_PROPERTY_ID.StorageAccessAlignmentProperty)

    def sqp_seek_penalty(self) -> bool:
        """Accepts drive and volume handles, but always returns related drive info."""

        return bool(
            self.storage_query_property(
                winioctl.STORAGE_PROPERTY_ID.StorageDeviceSeekPenaltyProperty, False
            ).IncursSeekPenalty
        )

    def sqp_trim_enabled(self) -> bool:
        """Accepts drive and volume handles, but always returns related drive info."""

        return bool(
            self.storage_query_property(winioctl.STORAGE_PROPERTY_ID.StorageDeviceTrimProperty, False).TrimEnabled
        )

    def sqp_temperature(self) -> dict:
        """Accepts drive and volume handles, but always returns related drive info."""

        # requires Windows 10+
        return self.storage_query_property(winioctl.STORAGE_PROPERTY_ID.StorageDeviceTemperatureProperty)

    def get_device_number(self) -> dict:
        """Returns for:
        - volumes: device type, device number and partition number
        - drives: device type, device number and partition number 0

        """

        InBuffer = EMPTY_BUFFER()
        OutBuffer = winioctl.STORAGE_DEVICE_NUMBER()
        MyDeviceIoControl(
            self.handle, winioctl.IOCTL_STORAGE_GET_DEVICE_NUMBER, InBuffer, OutBuffer, timeout_ms=self.timeout_ms
        )
        return struct2dict(OutBuffer)

    def read_capacity(self) -> dict:
        """Accepts drive and volume handles, but always returns related drive info.
        The DiskLength returned is the same as if `length_info` is used on the related drive.

        Requires read access rights.
        """

        InBuffer = EMPTY_BUFFER()
        OutBuffer = winioctl.STORAGE_READ_CAPACITY()
        MyDeviceIoControl(
            self.handle, winioctl.IOCTL_STORAGE_READ_CAPACITY, InBuffer, OutBuffer, timeout_ms=self.timeout_ms
        )
        return struct2dict(OutBuffer)

    def sqp_device(self) -> dict:
        """Accepts drive and volume handles, but always returns related drive info."""

        # obtain buffer size first
        InBuffer = winioctl.STORAGE_PROPERTY_QUERY()
        OutBuffer = winioctl.STORAGE_DESCRIPTOR_HEADER()
        InBuffer.PropertyId = winioctl.STORAGE_PROPERTY_ID.StorageDeviceProperty
        InBuffer.QueryType = winioctl.STORAGE_QUERY_TYPE.PropertyStandardQuery
        MyDeviceIoControl(
            self.handle, winioctl.IOCTL_STORAGE_QUERY_PROPERTY, InBuffer, OutBuffer, timeout_ms=self.timeout_ms
        )

        # query with correct buffer size
        InBuffer = winioctl.STORAGE_PROPERTY_QUERY()
        OutBuffer = winioctl.STORAGE_DEVICE_DESCRIPTOR_SIZE(
            OutBuffer.Size - sizeof(winioctl.STORAGE_DEVICE_DESCRIPTOR)
        )()
        InBuffer.PropertyId = winioctl.STORAGE_PROPERTY_ID.StorageDeviceProperty
        InBuffer.QueryType = winioctl.STORAGE_QUERY_TYPE.PropertyStandardQuery

        MyDeviceIoControl(
            self.handle, winioctl.IOCTL_STORAGE_QUERY_PROPERTY, InBuffer, OutBuffer, timeout_ms=self.timeout_ms
        )

        out = {
            "DeviceType": ScsiDriveType(OutBuffer.DeviceType),
            "DeviceTypeModifier": OutBuffer.DeviceTypeModifier,
            "RemovableMedia": bool(OutBuffer.RemovableMedia.value),
            "CommandQueueing": bool(OutBuffer.CommandQueueing.value),
            "BusType": OutBuffer.BusType.to_enum(),
        }

        raw = bytes(OutBuffer.RawDeviceProperties)
        offset = sizeof(winioctl.STORAGE_DEVICE_DESCRIPTOR_SIZE(0)())
        assert offset == 36
        assert OutBuffer.RawPropertiesLength in (0, offset)

        if OutBuffer.VendorIdOffset == 0:
            out["VendorId"] = None
        else:
            out["VendorId"] = cstring(raw, OutBuffer.VendorIdOffset - offset)

        if OutBuffer.ProductIdOffset == 0:
            out["ProductId"] = None
        else:
            out["ProductId"] = cstring(raw, OutBuffer.ProductIdOffset - offset)

        if OutBuffer.ProductRevisionOffset == 0:
            out["ProductRevision"] = None
        else:
            out["ProductRevision"] = cstring(raw, OutBuffer.ProductRevisionOffset - offset)

        if OutBuffer.SerialNumberOffset == 0:
            out["SerialNumber"] = None
        else:
            out["SerialNumber"] = cstring(raw, OutBuffer.SerialNumberOffset - offset)

        return out


class Volume(WindowsHandle, StorageMixin):
    @classmethod
    def from_win32_drive_letter_p(cls, path: str, mode: str = "r") -> Self:
        assert win32_drive_letter_p.match(path)
        return cls(open_device(path, mode))

    @classmethod
    def from_logical_drive(cls, path: str, mode: str = "r") -> Self:
        return cls(open_device(logical_drive_to_win32_device_path(path), mode))

    @classmethod
    def from_volume_guid_path(cls, path: str, mode: str = "r") -> Self:
        if not is_volume_guid_path(path):
            raise ValueError("path is not a volume guid path")

        volume_guid_path = path[:-1]  # important: remove trailing slash
        return cls(open_device(volume_guid_path, mode))

    @classmethod
    def from_harddisk_volume_index(cls, index: int, mode: str = "r") -> Self:
        return cls(open_device(f"\\\\.\\HarddiskVolume{index}", mode))

    @classmethod
    def from_disk_index_and_partition(cls, index: int, partition: int, mode: str = "r") -> Self:
        return cls(open_device(f"\\\\?\\Harddisk{index}Partition{partition}", mode))

    # FSCTL

    def lock(self) -> None:
        MyDeviceIoControl(self.handle, winioctl.FSCTL_LOCK_VOLUME, EMPTY_BUFFER(), EMPTY_BUFFER())

    def unlock(self) -> None:
        MyDeviceIoControl(self.handle, winioctl.FSCTL_UNLOCK_VOLUME, EMPTY_BUFFER(), EMPTY_BUFFER())

    def dismount(self) -> None:
        MyDeviceIoControl(self.handle, winioctl.FSCTL_DISMOUNT_VOLUME, EMPTY_BUFFER(), EMPTY_BUFFER())

    def is_mounted(self) -> bool:
        try:
            MyDeviceIoControl(self.handle, winioctl.FSCTL_IS_VOLUME_MOUNTED, EMPTY_BUFFER(), EMPTY_BUFFER())
            return True
        except OSError as e:
            if e.winerror == winerror.ERROR_NOT_READY:
                return False
            else:
                raise

    def extend(self) -> None:
        """Allows to read beyond the filesytem volume to read the full partition size,
        which might be slightly larger.
        Note: Might require unbuffered IO and manual management of read size,
            since the Python read() buffering can do out of bounds reads.
            Get the correct partition size with `length_info` or `partition_info`.
        """
        MyDeviceIoControl(self.handle, winioctl.FSCTL_ALLOW_EXTENDED_DASD_IO, EMPTY_BUFFER(), EMPTY_BUFFER())

    def filesystem_statistics(self) -> List[dict]:
        """Retrieves the information from various file system performance counters."""

        class FILESYSTEM_STATISTICS_NTFS(Structure):
            _fields_ = [
                ("fss", winioctl.FILESYSTEM_STATISTICS),
                ("fs", winioctl.NTFS_STATISTICS),
                ("padding", BYTE * 52),
            ]

        class FILESYSTEM_STATISTICS_FAT(Structure):
            _fields_ = [
                ("fss", winioctl.FILESYSTEM_STATISTICS),
                ("fs", winioctl.FAT_STATISTICS),
                ("padding", BYTE * 36),
            ]

        class FILESYSTEM_STATISTICS_EXFAT(Structure):
            _fields_ = [
                ("fss", winioctl.FILESYSTEM_STATISTICS),
                ("fs", winioctl.EXFAT_STATISTICS),
                ("padding", BYTE * 36),
            ]

        assert sizeof(FILESYSTEM_STATISTICS_NTFS) % 64 == 0
        assert sizeof(FILESYSTEM_STATISTICS_FAT) % 64 == 0
        assert sizeof(FILESYSTEM_STATISTICS_EXFAT) % 64 == 0

        InBuffer = EMPTY_BUFFER()
        OutBuffer = winioctl.FILESYSTEM_STATISTICS()
        try:
            MyDeviceIoControl(
                self.handle, winioctl.FSCTL_FILESYSTEM_GET_STATISTICS, InBuffer, OutBuffer, timeout_ms=self.timeout_ms
            )
        except OSError as e:
            if e.winerror != winerror.ERROR_MORE_DATA:
                raise

            fsmap = {
                FILESYSTEM_STATISTICS_TYPE.NTFS.value: FILESYSTEM_STATISTICS_NTFS,
                FILESYSTEM_STATISTICS_TYPE.FAT.value: FILESYSTEM_STATISTICS_FAT,
                FILESYSTEM_STATISTICS_TYPE.EXFAT.value: FILESYSTEM_STATISTICS_EXFAT,
            }
            OutBuffer = (fsmap[OutBuffer.FileSystemType] * os.cpu_count())()
            MyDeviceIoControl(
                self.handle, winioctl.FSCTL_FILESYSTEM_GET_STATISTICS, InBuffer, OutBuffer, timeout_ms=self.timeout_ms
            )

        out = [struct2dict(s) for s in OutBuffer]
        for d in out:
            d.pop("padding")
        return out

    def ntfs_volume_data(self) -> dict:
        class NTFS_VOLUME_DATA_COMBINED(Structure):
            _fields_ = [
                ("basic", winioctl.NTFS_VOLUME_DATA_BUFFER),
                ("extended", winioctl.NTFS_EXTENDED_VOLUME_DATA),
            ]

        InBuffer = EMPTY_BUFFER()
        OutBuffer = NTFS_VOLUME_DATA_COMBINED()
        MyDeviceIoControl(
            self.handle, winioctl.FSCTL_GET_NTFS_VOLUME_DATA, InBuffer, OutBuffer, timeout_ms=self.timeout_ms
        )
        return struct2dict(OutBuffer)

    def is_dirty(self):
        InBuffer = EMPTY_BUFFER()
        OutBuffer = ULONG()
        MyDeviceIoControl(self.handle, winioctl.FSCTL_IS_VOLUME_DIRTY, InBuffer, OutBuffer, timeout_ms=self.timeout_ms)
        return IsDirtyFlags(OutBuffer.value)

    # IOCTL_VOLUME

    def bring_online(self) -> None:
        MyDeviceIoControl(self.handle, winioctl.IOCTL_VOLUME_ONLINE, EMPTY_BUFFER(), EMPTY_BUFFER())

    def take_offline(self) -> None:
        MyDeviceIoControl(self.handle, winioctl.IOCTL_VOLUME_OFFLINE, EMPTY_BUFFER(), EMPTY_BUFFER())


class Drive(WindowsHandle, StorageMixin):
    @classmethod
    def from_drive_type_and_index(cls, drive_type: str, drive_index: int, mode: str = "r") -> Self:
        if drive_type.lower() not in ("physicaldrive", "scsi"):
            msg = f"Invalid drive type: {drive_type}"
            raise ValueError(msg)

        return cls(open_device(rf"\\.\{drive_type}{drive_index}", mode))

    @classmethod
    def from_scsi_index(cls, drive_index: int, mode: str = "r") -> Self:
        return cls(open_device(rf"\\.\Scsi{drive_index}:", mode))

    # IOCTL_DISK

    def verify_extent(self, start: int, length: int) -> None:
        """Can cause issues with some drivers (like TrueCrypt)."""

        InBuffer = winioctl.VERIFY_INFORMATION()
        OutBuffer = EMPTY_BUFFER()

        InBuffer.StartingOffset = start
        InBuffer.Length = length

        MyDeviceIoControl(self.handle, winioctl.IOCTL_DISK_VERIFY, InBuffer, OutBuffer, timeout_ms=self.timeout_ms)

    def is_writable(self) -> bool:
        try:
            MyDeviceIoControl(self.handle, winioctl.IOCTL_DISK_IS_WRITABLE, EMPTY_BUFFER(), EMPTY_BUFFER())
            return True
        except OSError as e:
            if e.winerror == winerror.ERROR_WRITE_PROTECT:
                return False
            else:
                raise

    def cache_information(self):
        InBuffer = EMPTY_BUFFER()
        OutBuffer = winioctl.DISK_CACHE_INFORMATION()

        MyDeviceIoControl(
            self.handle, winioctl.IOCTL_DISK_GET_CACHE_INFORMATION, InBuffer, OutBuffer, timeout_ms=self.timeout_ms
        )

        return struct2dict(OutBuffer)

    # IOCTL_STORAGE

    def sqp_device_protocol_specific(
        self,
        protocol_type: winioctl.STORAGE_PROTOCOL_TYPE,
        data_type: Union[winioctl.STORAGE_PROTOCOL_ATA_DATA_TYPE, winioctl.STORAGE_PROTOCOL_NVME_DATA_TYPE],
        request_value: Union[nvme.NVME_IDENTIFY_CNS_CODES, nvme.NVME_LOG_PAGES],
    ) -> dict:
        psd_size = sizeof(winioctl.STORAGE_PROTOCOL_SPECIFIC_DATA)

        if protocol_type == winioctl.STORAGE_PROTOCOL_TYPE.ProtocolTypeNvme:
            if data_type == winioctl.STORAGE_PROTOCOL_NVME_DATA_TYPE.NVMeDataTypeIdentify:
                mapping = {
                    nvme.NVME_IDENTIFY_CNS_CODES.NVME_IDENTIFY_CNS_SPECIFIC_NAMESPACE: nvme.NVME_IDENTIFY_NAMESPACE_DATA,
                    nvme.NVME_IDENTIFY_CNS_CODES.NVME_IDENTIFY_CNS_CONTROLLER: nvme.NVME_IDENTIFY_CONTROLLER_DATA,
                }

            elif data_type == winioctl.STORAGE_PROTOCOL_NVME_DATA_TYPE.NVMeDataTypeLogPage:
                mapping = {
                    nvme.NVME_LOG_PAGES.NVME_LOG_PAGE_HEALTH_INFO: nvme.NVME_HEALTH_INFO_LOG,
                }
            else:
                raise ValueError(f"Unsupported data_type: {data_type}")
        else:
            raise ValueError(f"Unsupported protocol_type: {protocol_type}")

        try:
            ProtocolData = mapping[request_value]
        except KeyError:
            raise ValueError(f"Unsupported request_value: {request_value}")

        class DUMMY(Structure):
            _fields_ = [("spq", winioctl.STORAGE_PROPERTY_QUERY_SIZE(psd_size)), ("pd", ProtocolData)]

        InBuffer = DUMMY()

        psd = winioctl.STORAGE_PROTOCOL_SPECIFIC_DATA()
        psd.ProtocolType = protocol_type
        psd.DataType = data_type
        psd.ProtocolDataRequestValue = request_value  # cdw10
        # psd.ProtocolDataRequestSubValue = 1  # If the ProtocolDataRequestValue is NVME_IDENTIFY_CNS_SPECIFIC_NAMESPACE, this will have a value of the namespace ID.
        psd.ProtocolDataOffset = psd_size  # DUMMY.pd.offset gives error 87
        psd.ProtocolDataLength = sizeof(ProtocolData)

        # InBuffer.PropertyId = winioctl.STORAGE_PROPERTY_ID.StorageAdapterProtocolSpecificProperty
        InBuffer.spq.PropertyId = winioctl.STORAGE_PROPERTY_ID.StorageDeviceProtocolSpecificProperty
        InBuffer.spq.QueryType = winioctl.STORAGE_QUERY_TYPE.PropertyStandardQuery
        InBuffer.spq.AdditionalParameters = struct_to_array(psd, (BYTE * psd_size))
        assert sizeof(InBuffer.spq) == 48

        MyDeviceIoControl(self.handle, winioctl.IOCTL_STORAGE_QUERY_PROPERTY, InBuffer, InBuffer)

        out = {
            "PropertyId": InBuffer.spq.PropertyId.value,
            "QueryType": InBuffer.spq.QueryType.value,
            "AdditionalParameters": struct2dict(psd),
            ProtocolData.__name__: struct2dict(InBuffer.pd),
        }

        out["AdditionalParameters"]["DataType"] = winioctl.STORAGE_PROTOCOL_NVME_DATA_TYPE(
            out["AdditionalParameters"]["DataType"]
        ).to_enum()
        if data_type == winioctl.STORAGE_PROTOCOL_NVME_DATA_TYPE.NVMeDataTypeIdentify:
            out["AdditionalParameters"]["ProtocolDataRequestValue"] = nvme.NVME_IDENTIFY_CNS_CODES(
                out["AdditionalParameters"]["ProtocolDataRequestValue"]
            ).to_enum()
        elif data_type == winioctl.STORAGE_PROTOCOL_NVME_DATA_TYPE.NVMeDataTypeLogPage:
            out["AdditionalParameters"]["ProtocolDataRequestValue"] = nvme.NVME_LOG_PAGES(
                out["AdditionalParameters"]["ProtocolDataRequestValue"]
            ).to_enum()

        assert psd.FixedProtocolReturnData == 0, psd.FixedProtocolReturnData
        return out

    def firmware_get_info(self):
        """Query detailed firmware information."""

        InBuffer = winioctl.STORAGE_HW_FIRMWARE_INFO_QUERY()
        OutBuffer = winioctl.STORAGE_HW_FIRMWARE_INFO()

        InBuffer.Size = sizeof(winioctl.STORAGE_HW_FIRMWARE_INFO_QUERY)

        MyDeviceIoControl(
            self.handle, winioctl.IOCTL_STORAGE_FIRMWARE_GET_INFO, InBuffer, OutBuffer, timeout_ms=self.timeout_ms
        )

        if OutBuffer.SlotCount > 1:
            logger.error("Device has more than one firmware slot. We only return the first one.")

        return struct2dict(OutBuffer)

    def predict_failure(self):
        InBuffer = EMPTY_BUFFER()
        OutBuffer = ntddstor.STORAGE_PREDICT_FAILURE()

        MyDeviceIoControl(
            self.handle, winioctl.IOCTL_STORAGE_PREDICT_FAILURE, InBuffer, OutBuffer, timeout_ms=self.timeout_ms
        )

        return struct2dict(OutBuffer)

    # IOCTL misc

    def get_smart_version(self) -> dict:
        """Usually only supported by ATA devices, ie. not by NVME or USB attached drives."""

        InBuffer = EMPTY_BUFFER()
        OutBuffer = winioctl.GETVERSIONINPARAMS()

        MyDeviceIoControl(self.handle, winioctl.SMART_GET_VERSION, InBuffer, OutBuffer, timeout_ms=self.timeout_ms)

        return struct2dict(OutBuffer)

    def get_scsi_address(self):
        InBuffer = EMPTY_BUFFER()
        OutBuffer = ntddscsi.SCSI_ADDRESS()

        MyDeviceIoControl(self.handle, ntddscsi.IOCTL_SCSI_GET_ADDRESS, InBuffer, OutBuffer, timeout_ms=self.timeout_ms)

        return struct2dict(OutBuffer)


def query_dos_devices(path: Optional[str] = None) -> List[str]:
    """Acceptable input paths:
    - `C:` -> '\\Device\\HarddiskVolume1'
    - `Volume{xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx}` -> '\\Device\\HarddiskVolume1'
    - `HarddiskVolume1` -> `\\Device\\HarddiskVolume1`
    - `Harddisk0Partition1` -> `\\Device\\HarddiskVolume1`
    - `CdRom0` -> `\\Device\\CdRom0`
    - `GLOBALROOT\\Device\\Harddisk0\\Partition1` -> `\\Device\\HarddiskVolume1`
    - `PhysicalDrive0` -> `\\Device\\Harddisk0\\DR0`
    - `scsi#disk...` -> `\\Device\\00000001`
    Not supported:
    - `GLOBALROOT\\Device\\HarddiskVolume1`
    - `GLOBALROOT\\Device\\Harddisk0\\DR0`
    - `GLOBALROOT\\Device\\00000001`
    """

    if path is not None:
        if path.endswith("\\"):
            raise ValueError("Trailing \\ are not supported")
        if path.startswith("\\\\?\\"):
            raise ValueError("Leading \\\\?\\ is not supported")

    ucchMax = 64 * 1024
    TargetPath = create_unicode_buffer(ucchMax)
    BufferLength = QueryDosDeviceW(path, TargetPath, ucchMax)

    result = memoryview(TargetPath)[: BufferLength - 2].tobytes().decode("utf-16-le")
    return result.split("\0")


def find_volumes() -> Iterator[str]:
    """Yields volume guid paths like `\\\\?\\Volume{xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx}\\`
    `os.listvolumes()` on Python 3.12+
    """

    BufferLength = 64 * 1024
    VolumeName = create_unicode_buffer(BufferLength)

    try:
        handle = FindFirstVolumeW(VolumeName, BufferLength)
    except OSError as e:
        if e.winerror == winerror.ERROR_NO_MORE_FILES:
            return
        raise

    try:
        while True:
            try:
                FindNextVolumeW(handle, VolumeName, BufferLength)
                yield VolumeName.value
            except OSError as e:
                if e.winerror == winerror.ERROR_NO_MORE_FILES:
                    break
                raise
    finally:
        FindVolumeClose(handle)


def find_volume_mount_points(volume_guid_path: str) -> List[str]:
    if not is_volume_guid_path(volume_guid_path):
        msg = f"Not a volume guid path: {volume_guid_path}"
        raise ValueError(msg)

    BufferLength = 64 * 1024
    VolumeMountPoint = create_unicode_buffer(BufferLength)

    try:
        handle = FindFirstVolumeMountPointW(volume_guid_path, VolumeMountPoint, BufferLength)
    except OSError as e:
        if e.winerror == winerror.ERROR_NO_MORE_FILES:
            return
        raise

    try:
        while True:
            try:
                FindNextVolumeMountPointW(handle, VolumeMountPoint, BufferLength)
                yield VolumeMountPoint.value
            except OSError as e:
                if e.winerror == winerror.ERROR_NO_MORE_FILES:
                    break
                raise
    finally:
        FindVolumeMountPointClose(handle)


def get_logical_drives() -> List[str]:
    """Get logical drives. Eg. ['C:\\\\', 'D:\\\\']
    Same as `os.listdrives()` on Python 3.12+
    """

    # BufferLength = GetLogicalDriveStringsW(0, None)
    BufferLength = 32 * 1024 - 1  # GetLogicalDriveStringsW fails with buffers >= 32k
    Buffer = create_unicode_buffer(BufferLength)
    ReturnLength = GetLogicalDriveStringsW(BufferLength, Buffer)
    # ReturnLength doesn't include the terminating null character
    assert ReturnLength < BufferLength
    result = memoryview(Buffer)[:ReturnLength].tobytes().decode("utf-16-le")
    if result:
        return result[:-1].split("\0")
    else:
        return []


def get_volume_path_names(volume_guid_path: str) -> List[str]:
    """Retrieves a list of drive letters and mounted folder paths for the specified volume.
    Same as `os.listmounts()` on Python 3.12+
    """

    if not is_volume_guid_path(volume_guid_path):
        msg = f"Not a volume guid path: {volume_guid_path}"
        raise ValueError(msg)

    BufferLength = 64 * 1024
    VolumePathNames = create_unicode_buffer(BufferLength)
    ReturnLength = DWORD()  # full buffer size including terminating null character

    GetVolumePathNamesForVolumeNameW(volume_guid_path, VolumePathNames, BufferLength, byref(ReturnLength))
    result = memoryview(VolumePathNames)[: ReturnLength.value - 1].tobytes().decode("utf-16-le")
    if result:
        return result[:-1].split("\0")
    else:
        return []


def get_volume_name(VolumeMountPoint: str) -> str:
    """Retrieves a volume GUID path for the volume that is associated with the specified volume mount point ( drive letter, volume GUID path, or mounted folder)."""

    BufferLength = 64 * 1024
    VolumeName = create_unicode_buffer(BufferLength)
    GetVolumeNameForVolumeMountPointW(VolumeMountPoint, VolumeName, BufferLength)
    return VolumeName.value


def enum_device_paths(
    setup_class: Optional[GUID] = None,
    interface_class: Optional[GUID] = None,
    enumerator: Optional[str] = None,
    device_instance_id: Optional[str] = None,
    default: bool = False,
    present: bool = True,
    profile: bool = False,
) -> Tuple[List[dict], List[str]]:
    flags = 0
    if default:
        flags |= setupapi.DIGCF_DEFAULT
    if present:
        flags |= setupapi.DIGCF_PRESENT
    if profile:
        flags |= setupapi.DIGCF_PROFILE

    if setup_class is None and interface_class is None:
        if enumerator is not None:
            enumerator = create_unicode_buffer(enumerator)

        hDevInfo = setupapi.SetupDiGetClassDevsW(None, enumerator, None, flags | setupapi.DIGCF_ALLCLASSES)
    elif setup_class is not None and interface_class is None:
        if enumerator is not None:
            enumerator = create_unicode_buffer(enumerator)

        hDevInfo = setupapi.SetupDiGetClassDevsW(byref(setup_class), enumerator, None, flags)
    elif setup_class is None and interface_class is not None:
        if device_instance_id is not None:
            device_instance_id = create_unicode_buffer(device_instance_id)

        hDevInfo = setupapi.SetupDiGetClassDevsW(
            byref(interface_class), device_instance_id, None, flags | setupapi.DIGCF_DEVICEINTERFACE
        )
    else:
        raise ValueError()

    device_infos = []
    device_paths = []

    try:
        if interface_class is None:
            DeviceInfoData = setupapi.SP_DEVINFO_DATA()
            DeviceInfoData.cbSize = sizeof(setupapi.SP_DEVINFO_DATA)

            while True:
                try:
                    setupapi.SetupDiEnumDeviceInfo(hDevInfo, len(device_infos), byref(DeviceInfoData))
                except OSError as e:
                    if e.winerror == winerror.ERROR_NO_MORE_ITEMS:
                        break
                    raise

                ClassDescription = create_unicode_buffer(setupapi.LINE_LEN)
                try:
                    setupapi.SetupDiGetClassDescriptionW(
                        byref(DeviceInfoData.ClassGuid), ClassDescription, setupapi.LINE_LEN, None
                    )
                except OSError as e:
                    if e.winerror == -536870394:  # ERROR_INVALID_CLASS
                        class_description = None
                    else:
                        raise
                else:
                    class_description = ClassDescription.value

                PropertyType = devpropdef.DEVPROPTYPE()
                PropertyBuffer = (BYTE * 4)()
                PropertyBufferSize = 4
                RequiredSize = DWORD()

                try:
                    setupapi.SetupDiGetDevicePropertyW(
                        hDevInfo,
                        byref(DeviceInfoData),
                        devpkey.DEVPKEY_Device_ProblemCode,
                        byref(PropertyType),
                        cast(PropertyBuffer, PBYTE),
                        PropertyBufferSize,
                        byref(RequiredSize),
                        0,
                    )
                    assert PropertyType.value == devpropdef.DEVPROP_TYPE_UINT32
                    devprop = cast(PropertyBuffer, POINTER(UINT32))[0]
                except OSError as e:
                    if e.winerror == winerror.ERROR_NOT_FOUND:
                        devprop = None
                    else:
                        raise

                device_infos.append(
                    {
                        "class-guid": str(DeviceInfoData.ClassGuid),
                        "device-instance": DeviceInfoData.DevInst,
                        "class-description": class_description,
                        "problem-code": devprop,
                    }
                )
        else:
            DeviceInterfaceData = setupapi.SP_DEVICE_INTERFACE_DATA()
            DeviceInterfaceData.cbSize = sizeof(setupapi.SP_DEVICE_INTERFACE_DATA)
            requiredSize = DWORD()

            while True:
                try:
                    setupapi.SetupDiEnumDeviceInterfaces(
                        hDevInfo, None, byref(interface_class), len(device_paths), byref(DeviceInterfaceData)
                    )
                except OSError as e:
                    if e.winerror == winerror.ERROR_NO_MORE_ITEMS:
                        break
                    raise
                assert DeviceInterfaceData.InterfaceClassGuid == interface_class

                try:
                    setupapi.SetupDiGetDeviceInterfaceDetailW(
                        hDevInfo, byref(DeviceInterfaceData), None, 0, byref(requiredSize), None
                    )
                except OSError as e:
                    if e.winerror == winerror.ERROR_INSUFFICIENT_BUFFER:
                        pass
                    else:
                        raise

                size = requiredSize.value - sizeof(setupapi.SP_DEVICE_INTERFACE_DETAIL_DATA_W)
                DeviceInterfaceDetailData = setupapi.SP_DEVICE_INTERFACE_DETAIL_DATA_W_SIZE(size)()
                DeviceInterfaceDetailData.cbSize = sizeof(setupapi.SP_DEVICE_INTERFACE_DETAIL_DATA_W)

                setupapi.SetupDiGetDeviceInterfaceDetailW(
                    hDevInfo,
                    byref(DeviceInterfaceData),
                    cast(byref(DeviceInterfaceDetailData), POINTER(setupapi.SP_DEVICE_INTERFACE_DETAIL_DATA_W)),
                    requiredSize,
                    None,
                    None,
                )

                device_paths.append(DeviceInterfaceDetailData.DevicePath)

    finally:
        setupapi.SetupDiDestroyDeviceInfoList(hDevInfo)

    return device_infos, device_paths


def enum_disks():
    device_infos, device_paths = enum_device_paths(interface_class=winioctl.GUID_DEVINTERFACE_DISK)
    for device_path in device_paths:
        out = {"DevicePath": device_path}
        with Drive.from_raw_path(device_path, "") as drive:
            dn = drive.get_device_number()
            dn.pop("PartitionNumber")
            out.update(dn)
            yield out


def enum_cdrom():
    device_infos, device_paths = enum_device_paths(interface_class=winioctl.GUID_DEVINTERFACE_CDROM)
    for device_path in device_paths:
        out = {"DevicePath": device_path}
        with Drive.from_raw_path(device_path, "") as drive:
            dn = drive.get_device_number()
            dn.pop("PartitionNumber")
            out.update(dn)
            yield out


if __name__ == "__main__":
    from argparse import ArgumentParser
    from pprint import pprint

    parser = ArgumentParser()
    parser.add_argument("driveindex", type=int)
    args = parser.parse_args()

    try:
        drive = Drive.from_drive_type_and_index("PhysicalDrive", args.driveindex, "r")
    except PermissionError:
        logging.warning("Opening drive with read access failed. Using no access.")
        drive = Drive.from_drive_type_and_index("PhysicalDrive", args.driveindex, "")

    with drive as d:
        try:
            print("Alignment:", d.sqp_alignment())
        except OSError as e:
            print("Alignment:", e)
        try:
            print("Seek penalty:", d.sqp_seek_penalty())
        except OSError as e:
            print("Seek penalty:", e)
        try:
            print("Trim enabled:", d.sqp_trim_enabled())
        except OSError as e:
            print("Trim enabled:", e)
        try:
            print("Capacity:", d.read_capacity())
        except OSError as e:
            print("Capacity:", e)
        print("Device:", d.sqp_device())
        try:
            print("Geometry:", d.drive_geometry())
        except OSError as e:
            print("Geometry:", e)
        try:
            print("SMART version:", d.get_smart_version())
        except OSError as e:
            print("SMART version:", e)
        try:
            print("Temperature:", d.sqp_temperature())
        except OSError as e:
            print("Temperature:", e)

        pprint(d.drive_layout())
