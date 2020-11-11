from __future__ import absolute_import, division, print_function, unicode_literals

from builtins import chr, zip
from future.moves.itertools import zip_longest

import errno
import logging
import os
import os.path
import platform
import re
import shutil
import stat
from fnmatch import fnmatch
from functools import partial
from operator import attrgetter
from typing import TYPE_CHECKING

from .compat import FileExistsError
from .compat.os import DirEntry, PathLike, fspath
from .compat.pathlib import Path
from .datetime import datetime_from_utc_timestamp
from .file import FILE_IO_BUFFER_SIZE, equal_files, iterfilelike
from .iter import is_empty
from .ops import logical_implication
from .os import _not_available, islink, uncabspath

if TYPE_CHECKING:
	from datetime import datetime
	from typing import Any, Callable, Iterable, Iterator, List, Optional, Set, Tuple, Union
	PathType = Union[str, PathLike]
	EntryType = Union[Path, DirEntry]

logger = logging.getLogger(__name__)

ascii_control = set(chr(i) for i in range(1, 32))
ntfs_illegal_chars = {"\0", "/"}
fat_illegal_chars = {"\0", "/", "?", "<", ">", "\\", ":", "*", "|", '"', "^"} # ^ really?

windows_ntfs_illegal_chars = ntfs_illegal_chars | {"\\", ":", "*", "?", "\"", "<", ">", "|"} | ascii_control
windows_fat_illegal_chars = fat_illegal_chars

windows_illegal_chars = windows_ntfs_illegal_chars | windows_fat_illegal_chars
unix_illegal_chars = {"\0", "/"}
mac_illegal_chars = {"\0", "/", ":"}

windows_sep = r"\/"
linux_sep = r"/"
mac_sep = r"/:"

windows_reserved_names = {"CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"}

class fileextensions(object):
	audio = ("wav", "mp3", "aac", "flac", "m4a", "m4b", "aiff", "ogg", "wma", "mka", "ac3", "dts")
	video = ("avi", "mp4", "m4v", "mkv", "mpg", "mpeg", "wmv", "mov", "flv", "f4v", "webm", "vob", "ogv", "m2ts", "rm", "rmvb", "asf", "3gp", "nsv", "divx", "ogm")
	images = ("bmp", "jpg", "jpeg", "png", "gif", "tif", "tiff", "tga")

	archives = ("zip", "rar", "ace", "tar", "tgz", "tbz", "7z", "cab", "dmg", "wim")
	bytecode = ("pyc", "class")
	configuration = ("ini", "toml", "conf", "reg")
	database = ("cat", "sqlite", "db")
	documents = ("txt", "pdf", "doc", "docx", "ps", "rtf", "pgs")
	executables = ("exe", "dll", "so", "scr", "msi", "pyd", "sys", "cpl")  # native code
	image_archives = ("cbz", "cbr", "cb7", "cbt", "cba")
	scripts = ("bat", "ps1", "sh", "c", "cpp", "cs", "py", "php", "js", "lua", "pl")  # and source code files

	disc_images_binary = ("iso", "bin", "mdf", "img")
	disc_images_sidecar = ("cue", "mds", "ccd")
	disc_images = disc_images_binary + disc_images_sidecar

	game_images = ("gcn", "nds", "3ds", "wad", "xbx", "gba", "gb", "nes", "sfc", "n64", "z64")
	compressed = ("gz", "bz2", "lzma", "xz", "z")
	subtitles = ("srt", "sub", "idx", "sup", "ssa", "ass")
	scene = ("nfo", "sfv")

	windows = ("library-ms", "desklink", "lnk", "dmp")
	macos = ("crash", )
	os = windows + macos

class IllegalFilename(ValueError):
	pass

class WindowsIllegalFilename(IllegalFilename):
	pass

class FileProperties(object):

	__slots__ = ("relpath", "size", "isdir", "abspath", "id", "modtime", "hash")

	def __init__(self, relpath, size, isdir, abspath=None, id=None, modtime=None, hash=None):
		# type: (str, int, bool, Optional[str], Optional[Any], Optional[datetime], Optional[str]) -> None

		self.relpath = relpath
		self.size = size
		self.isdir = isdir
		self.abspath = abspath
		self.id = id
		self.modtime = modtime
		self.hash = hash

	@classmethod
	def keys(cls):
		return cls.__slots__

	def values(self):
		return attrgetter(*self.__slots__)(self)

	def __iter__(self):
		# type: () -> tuple

		return self.values()

	def __repr__(self):
		# type: () -> str

		args = ("{}={!r}".format(k, v) for k, v in zip(self.keys(), self.values()) if v is not None)
		return "FileProperties({})".format(", ".join(args))

class DirEntryStub(object):
	__slots__ = ("name", "path")

	def __init__(self, name, path):
		self.name = name
		self.path = path

class BaseDirEntry(object):
	__slots__ = ("entry", )

	def __init__(self, entry):
		self.entry = entry

	@property
	def name(self):
		return self.entry.name

	@property
	def path(self):
		return self.entry.path

	def inode(self):
		return self.entry.inode()

	def is_dir(self):
		return self.entry.is_dir()

	def is_file(self):
		return self.entry.is_file()

	def is_symlink(self):
		return self.entry.is_symlink()

	def stat(self):
		return self.entry.stat()

	def __str__(self):
		return str(self.entry)

	def __repr__(self):
		return repr(self.entry)

	def __fspath__(self):
		return self.entry.path

class MyDirEntry(BaseDirEntry):
	__slots__ = ("basepath", "_relpath", "follow")

	def __init__(self, entry):
		BaseDirEntry.__init__(self, entry)

		self.basepath = None # type: Optional[str]
		self._relpath = None # type: Optional[str]
		self.follow = True

	@property
	def relpath(self):
		# type: () -> str

		if self._relpath is not None:
			return self._relpath

		if self.basepath is None:
			raise RuntimeError("relpath cannot be returned, because basepath is not set")

		self._relpath = os.path.relpath(self.entry.path, self.basepath)
		return self._relpath

	@relpath.setter
	def relpath(self, path):
		# type: (str, ) -> None

		self._relpath = path

if TYPE_CHECKING:
	MyDirEntryT = Union[DirEntry, MyDirEntry]

def mdatetime(path, aslocal=False):
	# type: (PathType, bool) -> datetime

	""" Returns the last modified date of `path`
		as a timezone aware datetime object.

		If `aslocal=True` it will be formatted as local time,
		and UTC otherwise (the default).
	"""

	if isinstance(path, (Path, DirEntry)):
		mtime = path.stat().st_mtime
	else:
		mtime = os.stat(path).st_mtime

	return datetime_from_utc_timestamp(mtime, aslocal)

def rename(old, new):
	# type: (PathType, PathType) -> None

	""" Renames `old` to `new`. Fails if `new` already exists.
		This is the default behaviour of `os.rename` on Windows.
		This function should do the same cross-platform.
		It is however not race free.
	"""

	# fixme: renaming a non-existing file in a non-existing folder yields a PermissionError not FileNotFoundError

	if os.path.exists(new):
		raise FileExistsError(new)

	os.renames(old, new) # fixme: don't use rename*s*

def copy_file_generator(source, dest, buffer_size=FILE_IO_BUFFER_SIZE, overwrite_readonly=False):
	# type: (PathType, PathType, int, bool) -> Iterator[None]

	""" Partial file is not deleted if exception gets raised anywhere. """

	try:
		os.makedirs(os.path.dirname(dest))
	except OSError as e:
		if e.errno != errno.EEXIST:
			raise

	if overwrite_readonly:
		try:
			make_writeable(dest)
		except OSError as e:
			if e.errno != errno.ENOENT:
				raise

	with open(source, "rb") as src, open(dest, "wb") as dst:
		for data in iterfilelike(src, chunk_size=buffer_size):
			dst.write(data)
			yield

	shutil.copystat(source, dest)

def st_mode_to_str(st_mode):
	# type: (int, ) -> str

	if stat.S_ISDIR(st_mode): return "directory"
	elif stat.S_ISREG(st_mode): return "regular file"
	elif stat.S_ISCHR(st_mode): return "character special device file"
	elif stat.S_ISBLK(st_mode): return "block special device file"
	elif stat.S_ISFIFO(st_mode): return "named pipe"
	elif stat.S_ISLNK(st_mode): return "symbolic link"
	elif stat.S_ISSOCK(st_mode): return "socket"
	else: return "unknown"

def append_to_filename(path, s):
	# type: (PathType, str) -> str

	""" Add `s` to the filename given in `path`. It's added before the extension, not after. """

	root, ext = os.path.splitext(path)
	return root + s + ext

def scandir_error_log(entry, exception):
	logger.exception("Error in %s", entry.path, exc_info=exception)

def scandir_error_raise(entry, exception):
	raise exception

def scandir_error_ignore(entry, exception):
	pass

def _scandir_rec_skippable(rootentry, files=True, others=False, follow_symlinks=True, errorfunc=scandir_error_raise):
	# type: (DirEntry, bool, bool, bool, Callable[[DirEntry, Exception], None]) -> Iterator[MyDirEntry]

	try:
		with os.scandir(rootentry.path) as it:
			for entry in it:
				if files and entry.is_file(follow_symlinks=follow_symlinks):
					yield MyDirEntry(entry)
				elif entry.is_dir(follow_symlinks=follow_symlinks):
					if not follow_symlinks and islink(entry): # must be a windows junction
						continue
					se = MyDirEntry(entry)
					yield se
					if se.follow:
						for e in _scandir_rec_skippable(entry, files, others, follow_symlinks, errorfunc):
							yield e
				else:
					if others:
						yield MyDirEntry(entry)
	except OSError as e:
		errorfunc(rootentry, e)

def _scandir_rec(rootentry, files=True, dirs=False, others=False, rec=True, follow_symlinks=True, errorfunc=scandir_error_raise):
	# type: (DirEntry, bool, bool, bool, bool, bool, Callable[[DirEntry, Exception], None]) -> Iterator[DirEntry]

	try:
		with os.scandir(rootentry.path) as it:
			for entry in it:
				if files and entry.is_file(follow_symlinks=follow_symlinks):
					yield entry
				elif entry.is_dir(follow_symlinks=follow_symlinks):
					if not follow_symlinks and islink(entry): # must be a windows junction
						continue
					if dirs:
						yield entry
					if rec:
						for e in _scandir_rec(entry, files, dirs, others, rec, follow_symlinks, errorfunc):
							yield e
				else:
					if others:
						yield entry
	except OSError as e:
		errorfunc(rootentry, e)

def scandir_rec(path, files=True, dirs=False, others=False, rec=True, follow_symlinks=True, relative=False, allow_skip=False, errorfunc=scandir_error_log):
	# type: (PathType, bool, bool, bool, bool, bool, bool, bool, Callable[[MyDirEntryT, Exception], None]) -> Iterator[MyDirEntryT]

	if not logical_implication(allow_skip, dirs and rec):
		raise ValueError("allow_skip implies dirs and rec")

	if isinstance(path, PathLike):
		path = fspath(path)

	entry = DirEntryStub(os.path.basename(path), uncabspath(path)) # for python 2 compat. and long filename support

	if not allow_skip:
		it = _scandir_rec(entry, files, dirs, others, rec, follow_symlinks, errorfunc)
	else:
		it = _scandir_rec_skippable(entry, files, others, follow_symlinks, errorfunc)

	if not relative:
		return it
	else:
		basepath = uncabspath(path)
		if not allow_skip:
			# entry is a `os.DirEntry`
			def modpathrelative(entry):
				entry = MyDirEntry(entry)
				entry.basepath = basepath
				return entry
		else:
			# entry is a `MyDirEntry`
			def modpathrelative(entry):
				entry.basepath = basepath
				return entry

		return map(modpathrelative, it)

def _scandir_depth(rootentry, depth, errorfunc):

	try:
		with os.scandir(rootentry.path) as it:
			for entry in it:
				if entry.is_dir():
					yield depth, entry
					for depth_entry in _scandir_depth(entry, depth + 1, errorfunc):
						yield depth_entry

		with os.scandir(rootentry.path) as it:
			for entry in it:
				if entry.is_file():
					yield depth, entry

	except OSError as e:
		errorfunc(rootentry, e)

def scandir_depth(path, depth=0, onerror=scandir_error_log):
	# type: (str, int, Callable) -> Iterator[Tuple[int, DirEntry]]

	""" Recursive version of `scandir` which yields the current path depth
		along with the DirEntry.
		Directories are returned first, then files.
		The order is arbitrary otherwise.
	"""

	entry = DirEntryStub(os.path.basename(path), uncabspath(path)) # for python 2 compat. and long filename support
	return _scandir_depth(entry, depth, onerror)

def make_readonly(path, stats=None):
	# type: (PathType, Optional[os.stat_result]) -> None

	"""deletes all write flags"""
	if not stats:
		stats = os.stat(path)
	os.chmod(path, stat.S_IMODE(stats.st_mode) & ~stat.S_IWUSR & ~stat.S_IWGRP & ~stat.S_IWOTH)

def make_writeable(path, stats=None):
	# type: (PathType, Optional[os.stat_result]) -> None

	"""set owner write flag"""
	if not stats:
		stats = os.stat(path)
	os.chmod(path, stat.S_IMODE(stats.st_mode) | stat.S_IWRITE)

def is_writeable(stats):
	# type: (os.stat_result, ) -> bool

	return stats.st_mode & stat.S_IWRITE != 0

def is_readable(stats):
	# type: (os.stat_result, ) -> bool

	return stats.st_mode & stat.S_IREAD != 0

def isfile(stats):
	# type: (os.stat_result, ) -> bool

	return stat.S_ISREG(stats.st_mode)

def isdir(stats):
	# type: (os.stat_result, ) -> bool

	return stat.S_ISDIR(stats.st_mode)

# was: islink
def statsislink(stats):
	# type: (os.stat_result, ) -> bool

	return stat.S_ISLNK(stats.st_mode)

def extract_basic_stat_info(stats):
	# type: (os.stat_result, ) -> tuple

	""" Returns size, modification, creation time and access mode. """
	return (stats.st_size, stats.st_mtime, stats.st_ctime, stats.st_mode)

def safe_filename(filename, replacement=""):
	# type: (str, str) -> str

	WIN = windows_illegal_chars
	UNIX = unix_illegal_chars
	MAC = mac_illegal_chars
	bad = set.union(WIN, UNIX, MAC)

	safe_filename_translation_table = str.maketrans({c: replacement for c in bad})

	return filename.translate(safe_filename_translation_table) # fixme: return callable which accepts only filename

safe_filename_simple = safe_filename

def _char_subber(s, illegal_chars, replacement):
	# type: (str, Set[str], str) -> str

	if set(replacement) & illegal_chars:
		raise ValueError("replace character cannot be a illegal character")

	regex = "[" + re.escape("".join(illegal_chars)) + "]"
	return re.sub(regex, replacement, s)

def _char_splitter(s, chars):
	# type: (str, Set[str]) -> List[str]

	regex = "[" + re.escape("".join(chars)) + "]"
	return re.split(regex, s)

def _special_subber(s, replacement="_"):
	# type: (str, str) -> str

	if s == "." or s == "..":
		return s.replace(".", replacement)

	return s

def windows_compliant_filename(filename, replacement="_"):
	# type: (str, str) -> str
	""" https://msdn.microsoft.com/en-us/library/aa365247.aspx """
	# reg. wikipedia: \x7f is valid!
	# trailing dots and spaces are ignored by windows

	ret = _char_subber(filename, windows_illegal_chars, replacement).rstrip(". ") # strip or replace?, translate

	root, _ = os.path.splitext(ret)

	if root.upper() in windows_reserved_names:
		raise WindowsIllegalFilename("filename would result in reserved name")

	return ret

def windows_compliant_dirname(filename, replacement):
	# type: (str, str) -> str
	""" https://msdn.microsoft.com/en-us/library/aa365247.aspx """
	# reg. wikipedia: \x7f is valid!
	# trailing dots and spaces are ignored by windows

	ret = _char_subber(filename, windows_illegal_chars, replacement).rstrip(" ")

	root, _ = os.path.splitext(ret)

	if root.upper() in windows_reserved_names:
		raise WindowsIllegalFilename("filename would result in reserved name")

	return ret

def linux_compliant_filename(filename, replacement="_"):
	# type: (str, str) -> str

	filename = _special_subber(filename, replacement)
	return _char_subber(filename, unix_illegal_chars, replacement)

def linux_compliant_dirname(filename, replacement="_"):
	# type: (str, str) -> str

	return _char_subber(filename, unix_illegal_chars, replacement)

def mac_compliant_filename(filename, replacement="_"):
	# type: (str, str) -> str

	filename = _special_subber(filename, replacement)
	return _char_subber(filename, mac_illegal_chars, replacement)

def mac_compliant_dirname(filename, replacement="_"):
	# type: (str, str) -> str

	return _char_subber(filename, mac_illegal_chars, replacement)

def windows_split_path(s):
	# type: (str, ) -> List[str]

	return _char_splitter(s, windows_sep)

def linux_split_path(s):
	# type: (str, ) -> List[str]

	return _char_splitter(s, linux_sep)

def mac_split_path(s):
	# type: (str, ) -> List[str]

	return _char_splitter(s, mac_sep)

system = platform.system()

if system == "Windows":
	compliant_filename = windows_compliant_filename
	compliant_dirname = windows_compliant_dirname
	split_path = windows_split_path
elif system == "Linux":
	compliant_filename = linux_compliant_filename
	compliant_dirname = linux_compliant_dirname
	split_path = linux_split_path
elif system == "Darwin":
	compliant_filename = mac_compliant_filename
	compliant_dirname = mac_compliant_dirname
	split_path = mac_split_path
else:
	compliant_filename = _not_available("compliant_filename")
	compliant_dirname = _not_available("compliant_dirname")
	split_path = _not_available("split_path")

def compliant_path(path, replace="_"):
	# type: (str, str) -> str

	fn_func = partial(compliant_dirname, replace=replace)
	path_compontents = split_path(path)

	ret = os.sep.join(map(fn_func, path_compontents[:-1]))
	ret = os.path.join(ret, compliant_filename(path_compontents[-1]))
	return ret

def reldirname(path):
	# type: (PathType, ) -> str

	ret = os.path.dirname(path)
	if not ret:
		ret = "."

	return ret

def equal_dirs_iter(dir1, dir2, follow_symlinks=False):

	""" Tests if two directories are equal. Doesn't handle links. """

	def entry_path_size(entry):
		return entry.path, entry.stat().st_size

	files1 = sorted(map(entry_path_size, scandir_rec(dir1, follow_symlinks=follow_symlinks))) # get rel paths
	files2 = sorted(map(entry_path_size, scandir_rec(dir2, follow_symlinks=follow_symlinks))) # get rel paths

	for (path1, size1), (path2, size2) in zip_longest(files1, files2):
		if path1 != path2:
			yield ("name", path1, path2)

		elif size1 != size2:
			yield ("size", path1, path2)

	for (path1, size1), (path2, size2) in zip_longest(files1, files2):
		if path1 == path2 and size1 == size2 and not equal_files(path1, path2):
			yield ("data", path1, path2)

def equal_dirs(dir1, dir2):
	return is_empty(equal_dirs_iter(dir1, dir2))

def realpath_win(path):
	# type: (PathType, ) -> str

	"""fix for os.path.realpath() which doesn't work under Win7"""

	path = os.path.abspath(path)
	if islink(path):
		return os.path.normpath(os.path.join(os.path.dirname(path), os.readlink(path)))
	else:
		return path

def search(directories, pattern, dirs=True, files=True, rec=True, follow_symlinks=False):
	# type: (Iterable[PathType], str, bool, bool, bool, bool) -> Iterator[DirEntry]

	""" Search for files and folders matching the wildcard `pattern`. """

	for directory in directories:
		for entry in scandir_rec(directory, dirs=dirs, files=files, rec=rec, follow_symlinks=follow_symlinks):
			if fnmatch(entry.name, pattern):
				yield entry

def rename_files_in_folder(path, pattern, transform, template, rec=True, follow_symlinks=False):
	# type: (PathType, str, Callable, str, bool, bool) -> None

	cpattern = re.compile(pattern)

	for entry in scandir_rec(path, files=True, dirs=False, rec=rec, follow_symlinks=follow_symlinks):
		filepath = entry.path
		base, name = os.path.split(filepath)

		m = cpattern.match(name)
		if not m:
			continue
		args = transform(*m.groups())

		to = template.format(*args)
		os.rename(filepath, os.path.join(base, to))

def clean_directory_by_extension(path, ext, rec=True, follow_symlinks=False):
	# type: (PathType, str, bool, bool) -> None

	""" Deletes all files of type `ext` if the same file without the ext exists
		and rename if it does not exit. """

	#delete .ext if normal file exists
	for entry in scandir_rec(path, files=True, dirs=False, rec=rec, follow_symlinks=follow_symlinks):
		filepath = entry.path
		if not filepath.endswith(ext):
			file_to_delete = filepath + ext
			if os.path.isfile(file_to_delete):
				logger.info("Remove: %s", file_to_delete)
				try:
					os.remove(file_to_delete)
				except OSError as e:
					logger.exception("Could not delete: %s", file_to_delete)
					break

	#rename all .ext to normal
	for entry in scandir_rec(path, files=True, dirs=False, rec=rec, follow_symlinks=follow_symlinks):
		filepath = entry.path
		if entry.name.endswith(ext):
			target = filepath[:-len(ext)]
			try:
				logger.info("Rename: %s -> %s", filepath, target)
				os.rename(filepath, target)
			except OSError as e:
				logger.exception("Should not have happened")
				break

def iter_links(path):
	# type: (PathType, ) -> Iterator[str]

	""" Yields all directory symlinks (and junctions on windows). """

	for dirpath, dirnames, filenames in os.walk(path):
		for dirname in dirnames:
			joined = os.path.join(dirpath, dirname)
			if islink(joined):
				yield joined

def normalize_seps(path):
	# type: (str, ) -> str

	""" Converts \ to /
	"""

	return path.replace("\\", "/")

def entrysuffix(entry):
	# type: (MyDirEntryT, ) -> str

	return os.path.splitext(entry.name)[1]

class Counts(object):
	__slots__ = ("dirs", "files", "others")

	def __init__(self):
		self.dirs = 0
		self.files = 0
		self.others = 0

	def __iadd__(self, other):
		# type: (Counts, ) -> None

		self.dirs += other.dirs
		self.files += other.files
		self.others += other.others

	def null(self):
		# type: () -> bool

		return self.dirs == 0 and self.files == 0 and self.others == 0

def _scandir_counts(rootentry, files=True, others=True, rec=True, total=False, errorfunc=scandir_error_raise):
	# type: (MyDirEntryT, bool, bool, bool, bool, Callable) -> Iterator[Tuple[DirEntry, Optional[Counts]]]

	counts = Counts()

	try:
		with os.scandir(rootentry.path) as it:
			for entry in it:

				if entry.is_dir():
					counts.dirs += 1
					if rec:
						for subentry, subcounts in _scandir_counts(entry, files, others, rec, total, errorfunc):
							yield subentry, subcounts

							if total:
								counts += subcounts

				elif entry.is_file():
					counts.files += 1
					if files:
						yield entry, None

				else:
					counts.others += 1
					if others:
						yield entry, None

		yield rootentry, counts  # yield after the loop

	except OSError as e:
		errorfunc(rootentry, e)

def scandir_counts(path, files=True, others=True, rec=True, total=False, onerror=scandir_error_log):
	# type: (PathType, bool, bool, bool, bool, Callable) -> Iterator[Tuple[DirEntry, Optional[Counts]]]

	""" A recursive variant of scandir() which also returns the number of files/directories
		within directories.
		If total is True, the numbers will be calculated recursively as well.
	"""

	entry = DirEntryStub(os.path.basename(path), uncabspath(path)) # for python 2 compat. and long filename support
	return _scandir_counts(entry, files, others, rec, total, onerror)

def shutil_onerror_remove_readonly(func, path, exc_info):

	""" onerror function for the `shutil.rmtree` function.
		Makes read-only files writable and tries again.
	"""

	stats = os.stat(path)
	if is_readable(stats):
		make_writeable(path, stats)
		func(path)
	else:
		raise
