from __future__ import absolute_import, division, print_function, unicode_literals

import re
from ctypes import wintypes, Structure, create_unicode_buffer, WinError, sizeof, byref
from ctypes.wintypes import BYTE

from cwinsdk import struct2dict
from cwinsdk.um.fileapi import CreateFileW, OPEN_EXISTING
from cwinsdk.um.ioapiset import DeviceIoControl
from cwinsdk.um.winnt import GENERIC_READ, GENERIC_WRITE, FILE_SHARE_READ, FILE_SHARE_WRITE
from cwinsdk.um.handleapi import INVALID_HANDLE_VALUE, CloseHandle
from cwinsdk.um.winioctl import PARTITION_IFS, PARTITION_MSFT_RECOVERY, DISK_GEOMETRY, IOCTL_DISK_GET_DRIVE_GEOMETRY, \
	IOCTL_DISK_GET_LENGTH_INFO, GET_LENGTH_INFORMATION, STORAGE_READ_CAPACITY, IOCTL_STORAGE_READ_CAPACITY, \
	STORAGE_PROPERTY_QUERY, STORAGE_PROPERTY_ID, STORAGE_QUERY_TYPE, STORAGE_ACCESS_ALIGNMENT_DESCRIPTOR, \
	IOCTL_STORAGE_QUERY_PROPERTY, FSCTL_LOCK_VOLUME, FSCTL_UNLOCK_VOLUME, STORAGE_DEVICE_DESCRIPTOR, \
	SMART_GET_VERSION, GETVERSIONINPARAMS, IOCTL_DISK_VERIFY, VERIFY_INFORMATION, FSCTL_ALLOW_EXTENDED_DASD_IO

from .handle import WindowsHandle

def get_length(path):
	# type: (str, ) -> int

	""" Returns for:
		partitions: the full partition size (might be larger than disk_usage().total)
		drives: the full drive size (might be larger than the one computed from the drive geometry)
	"""

	handle = open_device(path)
	try:
		InBuffer = EMPTY_BUFFER()
		OutBuffer = GET_LENGTH_INFORMATION()
		ret = MyDeviceIoControl(handle, IOCTL_DISK_GET_LENGTH_INFO, InBuffer, OutBuffer)

		return OutBuffer.Length

	finally:
		CloseHandle(handle)

class Volume(WindowsHandle):

	def __init__(self, path):
		# type: (str, ) -> None

		WindowsHandle.__init__()
		self.handle = open_logical_volume(path)

	def lock(self):
		MyDeviceIoControl(self.handle, FSCTL_LOCK_VOLUME, EMPTY_BUFFER(), EMPTY_BUFFER())

	def unlock(self):
		MyDeviceIoControl(self.handle, FSCTL_UNLOCK_VOLUME, EMPTY_BUFFER(), EMPTY_BUFFER())

	def extend(self):
		MyDeviceIoControl(self.handle, FSCTL_ALLOW_EXTENDED_DASD_IO, EMPTY_BUFFER(), EMPTY_BUFFER())

class Drive(WindowsHandle):

	def __init__(self, DriveIndex):
		# type: (int, ) -> None

		WindowsHandle.__init__()
		self.handle = open_physical_drive(DriveIndex)

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

		""" Accept drive and volume handles, but always returns related drive information.
			The DiskLength returned is the same as if `get_length` is used on the related drive.
		"""

		InBuffer = EMPTY_BUFFER()
		OutBuffer = STORAGE_READ_CAPACITY()
		ret = MyDeviceIoControl(self.handle, IOCTL_STORAGE_READ_CAPACITY, InBuffer, OutBuffer)

		return struct2dict(OutBuffer)

	# was: StorageQuery
	def get_device(self):
		# type: () -> dict

		InBuffer = STORAGE_PROPERTY_QUERY()
		OutBuffer = STORAGE_DEVICE_DESCRIPTOR()

		InBuffer.PropertyId = STORAGE_PROPERTY_ID.StorageDeviceProperty
		InBuffer.QueryType = STORAGE_QUERY_TYPE.PropertyStandardQuery
		InBuffer.AdditionalParameters = (BYTE*1)(0)

		MyDeviceIoControl(self.handle, IOCTL_STORAGE_QUERY_PROPERTY, InBuffer, OutBuffer)

		return struct2dict(OutBuffer)

	def get_geometry(self):

		InBuffer = EMPTY_BUFFER()
		OutBuffer = DISK_GEOMETRY()
		ret = MyDeviceIoControl(self.handle, IOCTL_DISK_GET_DRIVE_GEOMETRY, InBuffer, OutBuffer)

		return struct2dict(OutBuffer)

	def get_smart_version(self):
		# type: () -> dict

		InBuffer = EMPTY_BUFFER()
		OutBuffer = GETVERSIONINPARAMS()

		MyDeviceIoControl(self.handle, SMART_GET_VERSION, InBuffer, OutBuffer)

		return struct2dict(OutBuffer)

	def verify(self, start, length):
		# type: (int, int) -> None

		InBuffer = VERIFY_INFORMATION()
		OutBuffer = EMPTY_BUFFER()

		InBuffer.StartingOffset = start
		InBuffer.Length = length

		MyDeviceIoControl(self.handle, IOCTL_DISK_VERIFY, InBuffer, OutBuffer)

def get_drive_size(DriveIndex):
	with Drive(DriveIndex) as drive:
		geo = drive.get_geometry()
	return geo['Cylinders'] * geo['TracksPerCylinder'] * geo['SectorsPerTrack'] * geo['BytesPerSector']

class EMPTY_BUFFER(Structure):
	pass

assert sizeof(EMPTY_BUFFER) == 0

def partition_style_string(partition_style):
	return {0: "MBR", 1: "GPT"}.get(partition_style, "Unknown")

def partition_type_string(partition_type):
	return {PARTITION_IFS: "NTFS/exFAT", PARTITION_MSFT_RECOVERY: "Recovery"}.get(partition_type, "Unknown")

def MyDeviceIoControl(DeviceHandle, IoControlCode, InBuffer, OutBuffer, check_output=True):
	# type: (Any, Any, Any, Any, bool) -> None

	BytesReturned = wintypes.DWORD()

	assert IoControlCode

	ret = DeviceIoControl(
		DeviceHandle,
		IoControlCode,
		byref(InBuffer),
		sizeof(InBuffer),
		byref(OutBuffer),
		sizeof(OutBuffer),
		byref(BytesReturned),
		None
	)

	if ret == 0:
		raise WinError()

	if check_output:
		assert BytesReturned.value == sizeof(OutBuffer), "expected: {}, got: {}".format(sizeof(OutBuffer), BytesReturned.value)

def open_device(FileName):

	DeviceHandle = CreateFileW(
		FileName,
		GENERIC_READ|GENERIC_WRITE,
		FILE_SHARE_READ|FILE_SHARE_WRITE,
		None,
		OPEN_EXISTING,
		0,
		None
	)

	if DeviceHandle == INVALID_HANDLE_VALUE:
		raise WinError()

	return DeviceHandle

volumep = re.compile(r"^\\\\[\.\?]\\[A-Z]:$")
drivep = re.compile(r"^\\\\[\.\?]\\PHYSICALDRIVE[0-9]$")

def is_volume_or_drive(s):
	pre = "\\\\.\\"
	if not s.startswith(pre):
		s = pre + s

	s = s.upper()

	if volumep.match(s) or drivep.match(s):
		return s
	else:
		raise argparse.ArgumentTypeError("X: or PHYSICALDRIVEX")

def open_logical_volume(FileName):
	assert volumep.match(FileName)
	return open_device(FileName)

def open_physical_drive(DriveIndex):
	# type: (int, ) -> Any

	drive = r"\\.\PHYSICALDRIVE{}".format(DriveIndex)
	FileName = create_unicode_buffer(drive)

	return open_device(FileName)

def verify_drive_fast(d):
	from itertools import count
	from ..iter import progress

	gb = 1024**3
	for i in progress(count()):
		d.verify(i * gb, gb)

if __name__ == "__main__":
	with Drive(0) as d:
		print(d.get_alignment())
		print(d.get_capacity())
		print(d.get_device())
		print(d.get_geometry())
		print(d.get_smart_version())

		verify_drive_fast(d)
