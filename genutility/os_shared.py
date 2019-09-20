from __future__ import absolute_import, division, print_function, unicode_literals

import platform
from collections import namedtuple

_usagetuple = namedtuple("usage", "total used free")
_volumeinfotuple = namedtuple("volumeinfo", "VolumeName VolumeSerialNumber MaximumComponentLength FileSystemFlags FileSystemName")

def is_os_64bit():
	return platform.machine().endswith("64")
