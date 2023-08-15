import platform
from typing import NamedTuple

_usagetuple = NamedTuple("usage", [("total", int), ("used", int), ("free", int)])
_volumeinfotuple = NamedTuple(
    "volumeinfo",
    [
        ("VolumeName", str),
        ("VolumeSerialNumber", int),
        ("MaximumComponentLength", int),
        ("FileSystemFlags", int),
        ("FileSystemName", str),
    ],
)


def is_os_64bit():
    return platform.machine().endswith("64")
