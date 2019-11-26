from ctypes import wintypes, create_unicode_buffer, WinError, sizeof, byref

from cwinsdk.um.fileapi import CreateFileW, OPEN_EXISTING
from cwinsdk.um.ioapiset import DeviceIoControl
from cwinsdk.um.winnt import GENERIC_READ, GENERIC_WRITE, FILE_SHARE_READ, FILE_SHARE_WRITE
from cwinsdk.um.handleapi import INVALID_HANDLE_VALUE

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

def open_pysical_drive(DriveIndex):
	# type: (int, ) -> Any

	drive = r"\\.\PHYSICALDRIVE{}".format(DriveIndex)
	FileName = create_unicode_buffer(drive)
	BytesReturned = wintypes.DWORD()

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
