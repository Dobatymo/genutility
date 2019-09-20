from __future__ import absolute_import, division, print_function, unicode_literals

import os, signal, logging
from ctypes import byref, sizeof, create_unicode_buffer, WinError, cast, c_wchar_p, memset
from ctypes.wintypes import ULARGE_INTEGER, LPCWSTR, DWORD
from msvcrt import get_osfhandle
from typing import TYPE_CHECKING

from cwinsdk.shared.ehstorioctl import MAX_PATH
from cwinsdk.shared.ntdef import PWSTR
from cwinsdk.um.consoleapi import SetConsoleMode, GetConsoleMode, ENABLE_VIRTUAL_TERMINAL_PROCESSING
from cwinsdk.um.consoleapi2 import CONSOLE_SCREEN_BUFFER_INFO, GetConsoleScreenBufferInfo
from cwinsdk.um.fileapi import INVALID_FILE_ATTRIBUTES, GetDiskFreeSpaceExW, GetVolumeInformationW, LockFileEx, UnlockFileEx, GetFileAttributesW
from cwinsdk.um.processenv import GetStdHandle
from cwinsdk.um.combaseapi import CoTaskMemFree
from cwinsdk.um.ShlObj_core import SHGetKnownFolderPath
from cwinsdk.um.KnownFolders import FOLDERID_RoamingAppData
from cwinsdk.um.minwinbase import LOCKFILE_EXCLUSIVE_LOCK, LOCKFILE_FAIL_IMMEDIATELY, OVERLAPPED
from cwinsdk.um.WinBase import STD_OUTPUT_HANDLE
from cwinsdk.um.winnt import FILE_ATTRIBUTE_REPARSE_POINT

from .os_shared import _usagetuple, _volumeinfotuple

if TYPE_CHECKING:
	from typing import Tuple
	from ctypes.wintypes import HANDLE

unc_prefix = "\\\\?\\"

def get_stdout_handle():
	# type: () -> HANDLE

	""" Might return a redirect handle. For the real handle, use CreateFile("CONOUT$") """

	return GetStdHandle(STD_OUTPUT_HANDLE)

class EnableAnsi(object): # doesn't work for some reason...

	def __init__(self):
		# type: () -> None

		#os.system('') # calls cmd, which sets ANSI mode, but doesn't disable it when exiting (it's a bug probably)
		self.handle = get_stdout_handle()
		self.oldmode = DWORD()

		GetConsoleMode(self.handle, byref(self.oldmode))
		SetConsoleMode(self.handle, self.oldmode.value|ENABLE_VIRTUAL_TERMINAL_PROCESSING)

	def close(self):
		SetConsoleMode(self.handle, self.oldmode.value)

	def __enter__(self):
		return None

	def __exit__(self, *args):
		self.close()

def _islink(path):
	""" Tests if `path` refers to a symlink or a junction.
		- Python >= 3.2 `os.path.islink()` only supports symlinks, not junctions.
		- Python < 3.2 `os.path.islink()` always returns `False` on Windows.
		This function works in all cases.
	"""

	FileName = os.fspath(path)
	FileAttributes = GetFileAttributesW(FileName)

	if FileAttributes == INVALID_FILE_ATTRIBUTES:
		raise WinError()
	return FileAttributes & FILE_ATTRIBUTE_REPARSE_POINT == FILE_ATTRIBUTE_REPARSE_POINT

def _uncabspath(path):
	# type: (str, )-> str

	return unc_prefix+os.path.abspath(path)

def _lock(fp, exclusive=True, block=False):
	# type: (IO, bool, bool) -> None

	fd = fp.fileno()
	handle = get_osfhandle(fd)

	flags = 0
	if exclusive:
		flags |= LOCKFILE_EXCLUSIVE_LOCK
	if not block:
		flags |= LOCKFILE_FAIL_IMMEDIATELY

	overlapped = OVERLAPPED()
	memset(byref(overlapped), 0, sizeof(overlapped))

	LockFileEx(handle, flags, 0, 0xffffffff, 0xffffffff, overlapped)

def _unlock(fp):
	# type: (IO, bool, bool) -> None

	fd = fp.fileno()
	handle = get_osfhandle(fd)

	overlapped = OVERLAPPED()
	memset(byref(overlapped), 0, sizeof(overlapped))

	UnlockFileEx(handle, 0, 0xffffffff, 0xffffffff, overlapped)

def _get_appdata_dir():
	KF_FLAG_CREATE = 0x00008000

	rfid = byref(FOLDERID_RoamingAppData)
	Flags = 0
	Token = None
	Path = PWSTR()

	try:
		result = SHGetKnownFolderPath(rfid, KF_FLAG_CREATE, None, byref(Path))
	except OSError:
		logging.error("SHGetKnownFolderPath result: %X".format(result & 0xffffffff))
		raise

	ret = cast(Path, c_wchar_p).value
	CoTaskMemFree(Path)
	return ret

def _disk_usage_windows(path):
	# type: (str, ) -> _usagetuple

	DirectoryName = LPCWSTR(path)
	FreeBytesAvailableToCaller = ULARGE_INTEGER(0) # user free
	TotalNumberOfBytes = ULARGE_INTEGER(0) # user total
	TotalNumberOfFreeBytes = None # total free

	GetDiskFreeSpaceExW(DirectoryName, byref(FreeBytesAvailableToCaller), byref(TotalNumberOfBytes), TotalNumberOfFreeBytes)
	return _usagetuple(
		TotalNumberOfBytes.value,
		TotalNumberOfBytes.value-FreeBytesAvailableToCaller.value,
		FreeBytesAvailableToCaller.value
	)

def _volume_info_windows(path):
	# type: (str, ) -> _volumeinfotuple

	assert path.endswith("\\"), "X: usually doesn't work. X:\\ does."

	RootPathName = LPCWSTR(path)
	VolumeNameBuffer = create_unicode_buffer(MAX_PATH+1)
	VolumeNameSize = MAX_PATH+1
	VolumeSerialNumber = DWORD()
	MaximumComponentLength = DWORD()
	FileSystemFlags = DWORD()
	FileSystemNameBuffer = create_unicode_buffer(MAX_PATH+1)
	FileSystemNameSize = MAX_PATH+1

	GetVolumeInformationW(
		RootPathName,
		VolumeNameBuffer,
		VolumeNameSize,
		byref(VolumeSerialNumber),
		byref(MaximumComponentLength),
		byref(FileSystemFlags),
		FileSystemNameBuffer,
		FileSystemNameSize
	)

	return _volumeinfotuple(
		VolumeNameBuffer.value,
		VolumeSerialNumber.value,
		MaximumComponentLength.value,
		FileSystemFlags.value,
		FileSystemNameBuffer.value
	)

def _interrupt_windows():
	os.kill(os.getpid(), signal.CTRL_C_EVENT)

def _filemanager_cmd_windows(path):
	# type: (str, ) -> str

	return 'explorer.exe /select,"{}"'.format(path)

if __name__ == "__main__":
	s = '\033[35m'+'color-test'+'\033[39m'+" test end"
	print(s)
	with EnableAnsi():
		print(s)
	print(s)
