import platform
from typing import NamedTuple


class _usagetuple(NamedTuple):
    total: int
    used: int
    free: int


class _volumeinfotuple(NamedTuple):
    VolumeName: str
    VolumeSerialNumber: int
    MaximumComponentLength: int
    FileSystemFlags: int
    FileSystemName: str


def is_os_64bit():
    return platform.machine().endswith("64")
