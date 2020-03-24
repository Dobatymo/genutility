from __future__ import absolute_import, division, print_function, unicode_literals

from builtins import chr
from future.moves.itertools import zip_longest
import os, platform, stat, os.path, re, logging, shutil, errno
from operator import attrgetter
from fnmatch import fnmatch
from functools import partial
from typing import TYPE_CHECKING

from .file import equal_files, iterfilelike, FILE_IO_BUFFER_SIZE
from .iter import is_empty
from .os import islink, uncabspath
from .ops import logical_implication
from .string import replace_list
from .datetime import datetime_from_utc_timestamp
from .compat.os import PathLike, fspath, scandir

if __debug__:
	from .compat import gzip, bz2

if TYPE_CHECKING:
	from typing import Callable, Optional, Union, IO, TextIO, BinaryIO, Iterator
	PathType = Union[str, PathLike]

if __debug__:
	import unidecode

if TYPE_CHECKING:
	from typing import Callable, Union, Iterable, Iterator, Optional
	from pathlib import Path
	from .compat.os import DirEntry

logger = logging.getLogger(__name__)

ascii_control = set(chr(i) for i in range(1, 32))
ntfs_illegal_chars = {"\0", "/"}
fat_illegal_chars = {"\0", "/", '?', '<', '>', '\\', ':', '*', '|', '"', '^'} # ^ really?

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
	executables = ("exe", "dll", "so", "scr", "msi", "pyd", "sys")
	scripts = ("bat", "ps1", "sh", "py", "php")
	documents = ("txt", "pdf", "doc", "docx", "ps")
	image_archives = ("cbz", "cbr", "cb7", "cbt", "cba")

	disc_images_binary = ("iso", "bin", "mdf", "img")
	disc_images_sidecar = ("cue", "mds", "ccd")
	disc_images = disc_images_binary + disc_images_sidecar

	game_images = ("gcn", "nds", "3ds", "wad", "xbx", "gba", "gb", "nes", "sfc", "n64", "z64")
	compressed = ("gz", "bz2", "lzma", "xz", "z")
	subtitles = ("srt", "sub", "idx", "sup", "ssa", "ass")

	scene = ("nfo", "sfv")

class IllegalFilename(ValueError):
	pass

class WindowsIllegalFilename(IllegalFilename):
	pass

class FileProperties(object):

	__slots__ = ("relpath", "size", "isdir", "abspath", "id", "modtime", "hash")

	def __init__(self, relpath, size, isdir, abspath=None, id=None, modtime=None, hash=None):
		self.relpath = relpath
		self.size = size
		self.isdir = isdir
		self.abspath = abspath
		self.id = id
		self.modtime = modtime
		self.hash = hash

	def __iter__(self):
		return (self.relpath, self.size, self.isdir, self.abspath, self.id, self.modtime, self.hash)

	def __repr__(self):
		keys = self.__slots__
		values = attrgetter(*keys)(self)
		args = ("{}={!r}".format(k, v) for k, v in zip(keys, values) if v is not None)
		return "FileProperties({})".format(", ".join(args))

class DirEntryStub(object):
	__slots__ = ('name', 'path')

	def __init__(self, name, path):
		self.name = name
		self.path = path

class RelativeDirEntry(object):
	__slots__ = ('entry', 'basepath', 'relpath')

	def __init__(self, entry):
		self.entry = entry
		self.basepath = None # type: Optional[str]
		self.relpath = None # type: Optional[str]

	def __str__(self):
		return self._path

	def stat(self):
		return self.entry.stat()

	def is_dir(self):
		return self.entry.is_dir()

	def is_file(self):
		return self.entry.is_file()

	def is_symlink(self):
		return self.entry.is_symlink()

	def inode(self):
		return self.entry.inode()

	@property
	def name(self):
		return self.entry.name

	@property
	def path(self):
		if self.relpath is not None:
			return self.relpath
		assert self.basepath is not None
		self.relpath = os.path.relpath(self.entry.path, self.basepath)
		return self.relpath

	@property
	def abspath(self):
		return self.entry.path

class SkippableDirEntry(RelativeDirEntry):
	__slots__ = ('follow', )

	def __init__(self, entry):
		MyDirEntry.__init__(self, entry)
		self.follow = True

if TYPE_CHECKING:
	MyDirEntryT = Union[DirEntry, SkippableDirEntry]

def mdatetime(path):
	# type: (str, ) -> datetime

	""" Returns the last modified date of `path`. """

	return datetime_from_utc_timestamp(os.stat(path).st_mtime)

def rename(old, new):
	# type: (str, str) -> None

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
	# type: (str, str, int, bool) -> Iterator[None]

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
	# type: (DirEntry, bool, bool, bool, Callable[[DirEntry, Exception], None]) -> Iterator[SkippableDirEntry]

	try:
		with scandir(rootentry.path) as it: # python 3.6
			for entry in it:
				if files and entry.is_file(follow_symlinks=follow_symlinks):
					yield SkippableDirEntry(entry)
				elif entry.is_dir(follow_symlinks=follow_symlinks):
					if not follow_symlinks and islink(entry): # must be a windows junction
						continue
					se = SkippableDirEntry(entry)
					yield se
					if se.follow:
						for e in _scandir_rec_skippable(entry, files, others, follow_symlinks, errorfunc):
							yield e
				else:
					if others:
						yield SkippableDirEntry(entry)
	except OSError as e:
		errorfunc(rootentry, e)

def _scandir_rec(rootentry, files=True, dirs=False, others=False, rec=True, follow_symlinks=True, errorfunc=scandir_error_raise):
	# type: (DirEntry, bool, bool, bool, bool, bool, Callable[[DirEntry, Exception], None]) -> Iterator[DirEntry]

	try:
		with scandir(rootentry.path) as it: # python 3.6
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

	assert logical_implication(allow_skip, dirs and rec)

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
			def modpathrelative(entry):
				entry = RelativeDirEntry(entry)
				entry.basepath = basepath
				return entry
		else:
			# entry is already a SkippableDirEntry
			def modpathrelative(entry):
				entry.basepath = basepath
				return entry

		return map(modpathrelative, it)

def join_ext(name, ext):
	# type: (str, str) -> str

	""" adds extenions to name, eg. `join_ext("picture", "jpg") -> "picture.jpg" """

	return name + "." + ext

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
	return stats.st_mode & stat.S_IWRITE

def is_readable(stats):
	# type: (os.stat_result, ) -> bool
	return stats.st_mode & stat.S_IREAD

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

def safe_filename(filename, replace=""):
	# type: (str, str) -> str

	WIN = windows_illegal_chars
	UNIX = unix_illegal_chars
	MAC = mac_illegal_chars

	return replace_list(filename, set.union(WIN, UNIX, MAC), replace) # use translate or something similar fast

safe_filename_simple = safe_filename

def _char_subber(s, illegal_chars, replacement):
	# type: (str, Set[str], str) -> str

	if set(replacement) & illegal_chars:
		raise ValueError("replace character cannot be a illegal character")

	regex = "[" + re.escape("".join(illegal_chars)) + "]"
	return re.sub(regex, replacement, s)

def _char_splitter(s, chars):
	# type: (str, Set[str]) -> str

	regex = "[" + re.escape("".join(chars)) + "]"
	return re.split(regex, s)

def _special_subber(s, replacement="_"):
	# type: (str, str) -> str

	if s == "." or s == "..":
		return s.replace(".", replace)

	return s

def windows_compliant_filename(filename, replace="_"):
	# type: (str, str) -> str
	""" https://msdn.microsoft.com/en-us/library/aa365247.aspx """
	# reg. wikipedia: \x7f is valid!
	# trailing dots and spaces are ignored by windows

	ret = _char_subber(filename, windows_illegal_chars, replace).rstrip(". ") # strip or replace?, translate

	root, _ = os.path.splitext(ret)

	if root.upper() in windows_reserved_names:
		raise WindowsIllegalFilename("filename would result in reserved name")

	return ret

def windows_compliant_dirname(filename, replace):
	# type: (str, str) -> str
	""" https://msdn.microsoft.com/en-us/library/aa365247.aspx """
	# reg. wikipedia: \x7f is valid!
	# trailing dots and spaces are ignored by windows

	ret = _char_subber(filename, windows_illegal_chars, replace).rstrip(" ")

	root, _ = os.path.splitext(ret)

	if root.upper() in windows_reserved_names:
		raise WindowsIllegalFilename("filename would result in reserved name")

	return ret

def linux_compliant_filename(filename, replace="_"):
	filename = _special_subber(filename, replace)
	return _char_subber(filename, unix_illegal_chars, replace)

def linux_compliant_dirname(filename, replace="_"):
	return _char_subber(filename, unix_illegal_chars, replace)

def mac_compliant_filename(filename, replace="_"):
	filename = _special_subber(filename, replace)
	return _char_subber(filename, mac_illegal_chars, replace)

def mac_compliant_dirname(filename, replace="_"):
	return _char_subber(filename, mac_illegal_chars, replace)

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
	# type: (str, ) -> str

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
	# fixme: handle junctions

	path = os.path.abspath(path)
	if os.path.islink(path):
		return os.path.normpath(os.path.join(os.path.dirname(path), os.readlink(path)))
	else:
		return path

def convert_filenames_to_ascii(path, follow_symlinks=False):
	# type: (PathType, ) -> None
	""" convert all files in `path` to a ascii representation using unidecode """

	from unidecode import unidecode

	for entry in scandir_rec(path, files=True, dirs=False, rec=False, follow_symlinks=follow_symlinks):
		filepath = entry.path
		base, name = os.path.split(filepath)
		os.rename(filepath, os.path.join(base, unidecode(name)))

def search(directories, pattern, dirs=True, files=True, rec=True, follow_symlinks=False):
	# type: (Iterable[PathType], str, bool, bool, bool) -> Iterator[DirEntry]

	""" Search for files and folders matching the wildcard `pattern`. """

	for directory in directories:
		for entry in scandir_rec(directory, dirs=dirs, files=files, rec=rec, follow_symlinks=follow_symlinks):
			if fnmatch(entry.name, pattern):
				yield entry

def rename_files_in_folder(path, pattern, transform, template, rec=True, follow_symlinks=False):
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
	# type: (str, str, bool, bool) -> None

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
