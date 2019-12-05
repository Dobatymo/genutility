from msvcrt import get_osfhandle, open_osfhandle
from os import fdopen

from cwinsdk.um.handleapi import CloseHandle
from cwinsdk.um.winnt import GENERIC_READ, GENERIC_WRITE

_mode2access = {"": 0, "r": GENERIC_READ, "w": GENERIC_WRITE, "w+": GENERIC_READ | GENERIC_WRITE}

class WindowsHandle(object):

	def __init__(self):
		self.doclose = True

	@classmethod
	def from_file(cls, fp):
		return cls.from_fd(fp.fileno())

	@classmethod
	def from_fd(cls, fd):
		ret = cls.__new__(cls)
		ret.handle = get_osfhandle(fd)
		ret.doclose = False
		return ret

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
		if self.doclose:
			self.close()
