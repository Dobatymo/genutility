from __future__ import absolute_import, division, print_function, unicode_literals

from ctypes import byref, sizeof
from ctypes import GetLastError, FormatError, WinError
from errno import EACCES
from msvcrt import get_osfhandle, open_osfhandle
from os import fdopen

from cwinsdk.windows import (
	CloseHandle, CreateFileW, OpenFileById, GetFileInformationByHandleEx,
	GENERIC_READ, GENERIC_WRITE, OPEN_EXISTING, ERROR_SHARING_VIOLATION,
	FILE_ID_DESCRIPTOR, FILE_ID_INFO, # structs
	FILE_ID_TYPE, FILE_INFO_BY_HANDLE_CLASS, # enums
)
from cwinsdk.um.handleapi import INVALID_HANDLE_VALUE
from cwinsdk.um.winnt import FILE_GENERIC_READ, FILE_GENERIC_WRITE, FILE_SHARE_READ, FILE_SHARE_WRITE

class SharingViolation(OSError):
	pass

class WindowsFile(object):

	def __init__(self, handle):
		assert isinstance(handle, int)
		self.handle = handle

	def get_fd(self, flags):
		return open_osfhandle(self.handle, flags)

	def get_file(self, flags, mode="r", buffering=-1, encoding=None, errors=None, newline=None, closefd=True):
		return fdopen(self.get_fd(flags), mode, buffering, encoding, errors, newline, closefd)

	def close(self):
		if CloseHandle(self.handle) == 0:
			raise WinError()

	def __enter__(self):
		return self

	def __exit__(self, exc_type, exc_value, traceback):
		self.close()

	@classmethod
	def from_file(cls, fp):
		return cls.from_fd(fp.fileno())

	@classmethod
	def from_fd(cls, fd):
		handle = get_osfhandle(fd)
		return cls(handle)

	@classmethod
	def from_path(cls, path, mode="r", shared=False):
		# shared: allow write access from other processes

		if mode == "r":
			DesiredAccess = GENERIC_READ
		elif mode == "w":
			DesiredAccess = GENERIC_WRITE
		else:
			raise ValueError("Unsupported mode")

		if shared:
			ShareMode = FILE_SHARE_READ|FILE_SHARE_WRITE
		else:
			ShareMode = FILE_SHARE_READ

		SecurityAttributes = None
		CreationDisposition = OPEN_EXISTING
		FlagsAndAttributes = 0

		handle = CreateFileW(path, DesiredAccess, ShareMode, SecurityAttributes,
			CreationDisposition, FlagsAndAttributes, None)

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
		VolumeHint = None # open volume handle here
		FileId = FILE_ID_DESCRIPTOR(Size=..., Type=FILE_ID_TYPE.ExtendedFileIdType)
		DesiredAccess = GENERIC_READ
		ShareMode = FILE_SHARE_READ|FILE_SHARE_WRITE
		lpSecurityAttributes = None
		FlagsAndAttributes = 0

		handle = OpenFileById(VolumeHint, byref(FileId), DesiredAccess, ShareMode, lpSecurityAttributes, FlagsAndAttributes)
		return cls(handle)

	def info(self):
		FileInformation = FILE_ID_INFO()
		GetFileInformationByHandleEx(self.handle, FILE_INFO_BY_HANDLE_CLASS.FileIdInfo, byref(FileInformation), sizeof(FileInformation))
		return FileInformation

def is_open_for_write(path):
	try:
		with WindowsFile.from_path(path, mode="r", shared=False):
			return False
	except SharingViolation:
		return True

if __name__ == "__main__":
	path = "E:/empty.txt"
	with WindowsFile.from_path(path, mode="r", shared=False) as wf:
		print(wf.info().VolumeSerialNumber)
		print(bytes(wf.info().FileId))
