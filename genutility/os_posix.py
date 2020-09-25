from __future__ import absolute_import, division, print_function, unicode_literals

import fcntl
import os
import signal
from typing import TYPE_CHECKING

from .os_shared import _usagetuple

if TYPE_CHECKING:
	from typing import IO

def _lock(fp, exclusive=True, block=False):
	# type: (IO, bool, bool) -> None

	if exclusive:
		operation = fcntl.LOCK_EX
	else:
		operation = fcntl.LOCK_SH

	if not block:
		operation |= fcntl.LOCK_NB

	fcntl.flock(fp, operation)

def _unlock(fp):
	# type: (IO, ) -> None
	fcntl.flock(fp, fcntl.LOCK_UN)

def _disk_usage_posix(path):
	# type: (str, ) -> _usagetuple

	st = os.statvfs(path)

	total = st.f_blocks * st.f_frsize
	free = st.f_bavail * st.f_frsize

	return _usagetuple(total, total-free, free)

def _interrupt_posix():
	os.kill(os.getpid(), signal.SIGINT)

def _filemanager_cmd_posix(path):
	# type: (str, ) -> str

	return "nautilus \"{}\"".format(path) #gnome only. xdg-open for the rest?
