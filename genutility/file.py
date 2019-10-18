from __future__ import absolute_import, division, print_function, unicode_literals

import os.path
from sys import version_info
from io import open, TextIOWrapper, TextIOBase, RawIOBase, BufferedIOBase, SEEK_SET, SEEK_END
from typing import TYPE_CHECKING

from .iter import iter_equal, consume, resizer
from .math import PosInfInt
from .ops import logical_xor, logical_implication

if __debug__:
	from .compat import gzip, bz2

if TYPE_CHECKING:
	from typing import Callable, Optional, Union, IO, TextIO, BinaryIO

FILE_IO_BUFFER_SIZE = 8*1024*1024

def read_file(path, mode="b", encoding=None, errors=None):
	# type: (str, str, Optional[str]) -> bytes

	""" Reads and returns whole file. If content is not needed use consume_file()"""

	assert (encoding is None) == ("b" in mode)

	if not "r" in mode:
		mode = "r" + mode

	with open(path, mode, encoding=encoding, errors=errors) as fr:
		return fr.read()

def write_file(data, path, mode="wb", encoding=None, errors=None):
	# type: (str, Union[str, bytes], str, Optional[str]) -> None

	""" Writes file. """

	assert (encoding is None) == ("b" in mode)

	with open(path, mode, encoding=encoding, errors=errors) as fw:
		fw.write(data)

def linefileiter(fin, check_last=True): # kinda unnecessary
	last = None
	for line in fin:
		yield line
		last = line
	assert last.endswith("\n"), "File does not end in newline: {}".format(last)

def get_file_range(path, start, size):
	# type: (str, int, int) -> bytes

	with open(path, "rb") as fp:
		fp.seek(start)
		return fp.read(size)

def truncate_file(path, size):
	# type: (str, int) -> None

	with open(path, "r+b") as fp:
		fp.truncate(size)

def wrap_text(bf, mode, encoding, errors, newline):
	if "t" in mode:
		return TextIOWrapper(bf, encoding, errors, newline)
	return bf

def copen(file, mode="rt", archive_file=None, encoding=None, errors=None, newline=None, compresslevel=9):
	# type: (str, str, Optional[str], Optional[str], Optional[str], Optional[str], int) -> IO

	"""
	`compresslevel`: 0-9, 0: no compression, 1: least, 9: highest compression
	"""

	is_text = "t" in mode
	is_binary = "b" in mode

	assert logical_xor(is_text, is_binary), "Explicit text or binary mode required: {}".format(mode)
	assert logical_implication(is_binary, encoding is None and errors is None)

	if is_text:
		encoding = encoding or "utf-8"
		errors = errors or "strict"

	ext = os.path.splitext(file)[1].lower()
	if ext == '.gz':
		from .compat import gzip
		return gzip.open(file, mode, compresslevel=compresslevel, encoding=encoding, errors=errors, newline=newline)

	elif ext == '.bz2':
		from .compat import bz2
		return bz2.open(file, mode, compresslevel=compresslevel, encoding=encoding, errors=errors, newline=newline)

	elif ext == '.zip':
		assert archive_file, "archive_file must be specified"
		from zipfile import ZipFile

		newmode = "".join(set(mode) - {"t", "b"})

		with ZipFile(file, newmode) as zf: # note: even if the outer zip file is closed, the inner file can still be read apparently
			if version_info >= (3, 6):
				bf = zf.open(archive_file, newmode, force_zip64=True)
			else:
				bf = zf.open(archive_file, newmode)

		return wrap_text(bf, mode, encoding, errors, newline)

	return open(file, mode, encoding=encoding, errors=errors, newline=newline)

# was: OpenAndDeleteOnError, OpenFileRemoveOnException
class OpenFileAndDeleteOnError(object):

	""" Context manager which opens a file using the same arguments as `open`,
		but deletes the file in case an exception occurs after opening.
	"""

	def __init__(self, file, mode="rt", encoding=None, errors=None, newline=None, compresslevel=9):
	# type: (str, str, Optional[str], Optional[str], Optional[str], int) -> None

		is_text = "t" in mode
		is_binary = "b" in mode

		assert logical_xor(is_text, is_binary), "Explicit text or binary mode required: {}".format(mode)
		assert logical_implication(is_binary, encoding is None and errors is None)

		if is_text:
			encoding = encoding or "utf-8"
			errors = errors or "strict"

		self.file = file
		self.mode = mode
		self.encoding = encoding
		self.errors = errors
		self.newline = newline
		self.compresslevel = compresslevel
		self.fp = None # type: Optional[IO]

	def __enter__(self):
		# type: () -> IO

		self.fp = copen(self.file, self.mode, None, self.encoding, self.errors, self.newline, self.compresslevel)
		return self.fp

	def __exit__(self, exc_type, exc_value, traceback):
		self.fp.close()
		if exc_type:
			# fixme: race condition
			# use https://stackoverflow.com/a/3594593 and `ReOpenFile` on Windows
			# or SetFileInformationByHandle
			# see also: https://nullprogram.com/blog/2016/08/07/
			os.remove(self.file)

class PathOrBinaryIO(object):

	def __init__(self, fname, mode="rb", close=False):
		# type: (Union[str, BinaryIO],  str, str, str, Optional[str], bool) -> None

		if isinstance(fname, (RawIOBase, BufferedIOBase)):
			self._close = close
			self.fp = fname
		else:
			self._close = True
			self.fp = copen(fname, mode)

	def __enter__(self):
		return self.fp

	def __exit__(self, exc_type, exc_value, traceback):
		if self._close:
			self.fp.close()

class PathOrTextIO(object):

	def __init__(self, fname, mode="rt", encoding="utf-8", errors="strict", newline=None, close=False):
		# type: (Union[str, TextIO],  str, str, str, Optional[str], bool) -> None

		if isinstance(fname, TextIOBase):
			self.close = close
			self.fp = fname
		else:
			self.close = True
			self.fp = copen(fname, mode, encoding=encoding, errors=errors, newline=newline)

	def __enter__(self):
		return self.fp

	def __exit__(self, exc_type, exc_value, traceback):
		if self.close:
			self.fp.close()

class LastLineFile(object):

	chunk_size = 1024 * 4
	nl = "\n"

	def __init__(self, path, mode="rt+"):
		self.f = open(path, mode)
		self.ll_pos = None

	def __enter__(self):
		return self

	def __exit__(self, *args):
		self.close()

	def close(self):
		self.f.close()

	def _seek_to_last_line(self):
		if self.ll_pos is None:
			self.ll_pos = self._get_last_line_pos()

		self.f.seek(self.ll_pos, SEEK_SET)

	def _get_last_line_pos(self):
		self.f.seek(0, SEEK_END)
		pos = self.f.tell()
		ret_pos = 0
		while pos > 0:
			seek_next = max(pos - self.chunk_size, 0)
			self.f.seek(seek_next, SEEK_SET)
			chunk = self.f.read(pos - seek_next)
			fpos = chunk.rfind("\n")
			if fpos != -1:
				ret_pos = seek_next + fpos + 1
				if ret_pos != pos:
					break
			pos = seek_next
		return ret_pos

	def _validate(self, s):
		if self.nl in s:
			raise ValueError("Newline in input")

	def read(self):
		self._seek_to_last_line()
		return self.f.read()

	def newline(self, s):
		self.f.seek(0, SEEK_END)
		ret = self.f.write(self.nl)
		self.ll_pos = self.f.tell()
		return ret

	def replace(self, s):
		self._validate(s)
		self._seek_to_last_line()
		ret = self.f.write(s)
		self.f.truncate()
		return ret

class Tell(object):

	def __init__(self, fp):
		# type: (FileLike, ) -> None

		try:
			assert fp.seekable() == False
		except AttributeError:
			pass

		self._fp = fp
		self._pos = 0

	# wrapped

	def read(self, size=None): # the docs for `io.BufferedIOBase` say that size=-1, but that's not true for `HTTPResponse`
		ret = self._fp.read(size)
		self._pos += len(ret)
		return ret

	def read1(self, n=-1):
		ret = self._fp.read1(n)
		self._pos += len(ret)
		return ret

	def readall(self):
		ret = self._fp.readall()
		self._pos += len(ret)
		return ret

	def readline(self, limit=-1):
		ret = self._fp.readline(limit)
		self._pos += len(ret)
		return ret

	def readlines(self, hint=-1):
		raise NotImplementedError
		return self._fp.readlines(hint)

	def readinto(self, b):
		ret = self._fp.readinto(b)
		self._pos += ret
		return ret

	def readinto1(self, b):
		ret = self._fp.readinto1(b)
		self._pos += ret
		return ret

	def write(self, b): # fixme: should this be added to _pos?
		return self._fp.write(b)

	def writelines(self, lines): # fixme: should this be added to _pos?
		return self._fp.writelines(lines)

	def seek(self, offset, whence=SEEK_SET):
		raise IOError("Stream is not seekable")

	def tell(self):
		return self._pos

	# redirected

	def close(self):
		return self._fp.close()

	def detach(self):
		return self._fp.detach()

	def fileno(self):
		return self._fp.fileno()

	def flush(self):
		return self._fp.flush()

	def isatty(self):
		return self._fp.isatty()

	def readable(self):
		return self._fp.readable()

	def seekable(self):
		return self._fp.seekable()

	def truncate(self, size=None):
		return self._fp.truncate(size)

	def writable(self):
		return self._fp.writable()

from future.moves.urllib import response
from collections import deque

class BufferedTell(response.addinfourl): # fixme: untested!!!

	def __init__(self, filesize):
		#response.addinfourl.__init__(self, *args, **kwargs)
		self._pos = 0
		self._read = 0
		self.filesize = filesize
		self.buf = deque(maxlen=1024)

	def read(self, num=-1):
		if num == -1:
			num = self.filesize - self._pos
			print("num=-1")
		if self._pos == self._read:
			self._pos += num
			self._read += num
			data = response.addinfourl.read(num)
			self.buf.extend(data)
			return data
		elif self._pos < self._read:
			delta = self._read - self._pos
			self._pos += num
			if num <= delta:
				data = b"".join(self.buf.pop() for i in range(delta))
				self.buf.extend(data[::-1])
				return data[-1:-1-num:-1]
			else:
				datab = b"".join(self.buf.pop() for i in range(delta))
				datab = datab[::-1]
				self.buf.extend(datab)
				dataf = response.addinfourl.read(num - delta)
				self.buf.extend(dataf)
				return datab + dataf
		else:
			#return b""
			raise Exception("Unbuffered read")

	def tell(self):
		return self._pos

	def seek(self, offset, whence=0):
		if whence == 0:
			self._pos = offset
		elif whence == 1:
			self._pos += offset
		elif whence == 2:
			self._pos = self.filesize - offset
		else:
			raise ValueError("Unknown whence")

def copyfilelike(fin, fout, amount=None, buffer=FILE_IO_BUFFER_SIZE, report=None):
	# type: (IO, IO, Optional[int], Optional[int], Optional[Callable]) -> int

	""" Read data from `fin` in chunks of size `buffer` and write them to `fout`.
		Optionally limit the amout of data to `amount`. `report` can be a callable which receives
		the total number of bytes copied and bytes remaining.
		see `shutil.copyfileobj`
	"""

	# todo: have different input and output buffers

	amount = amount or PosInfInt

	copied = 0
	while amount > 0:
		if report:
			report(copied, amount+copied)

		data = fin.read(min(buffer, amount))

		if not data:
			break
		fout.write(data)
		amount -= len(data)
		copied += len(data)
	return copied

def simple_file_iter(fr, chunk_size=FILE_IO_BUFFER_SIZE):
	# type: (IO, int) -> Iterator

	""" Iterate file-like object `fr` and yield chunks of size `chunk_size`. """

	assert isinstance(chunk_size, int), "chunk_size needs to be an integer"

	#return iter(partial(fr.read, chunk_size), "") sentinel cannot be defined well
	while True:
		data = fr.read(chunk_size)
		if data:
			yield data
		else:
			break

def reversed_file_iter(fp, chunk_size=FILE_IO_BUFFER_SIZE):
	# type: (IO, int) -> Iterator

	""" Generate blocks of file's contents in reverse order. """

	fp.seek(0, SEEK_END)
	here = fp.tell()
	while here > 0:
		delta = min(chunk_size, here)
		here -= delta
		fp.seek(here, SEEK_SET)
		yield fp.read(delta)

def limited_file_iter(fr, amount, chunk_size=FILE_IO_BUFFER_SIZE):
	# type: (IO, int, int) -> Iterator

	""" Iterate file-like object `fr` and yield chunks of size `chunk_size`.
		Limit output to `amount` bytes.
	"""

	while amount > 0:
		data = fr.read(min(chunk_size, amount))
		if not data:
			break
		yield data
		amount -= len(data)

def iterfilelike(fr, amount=None, chunk_size=FILE_IO_BUFFER_SIZE):
	# type: (IO, Optional[int], int) -> Iterator

	""" Iterate file-like object `fr` and yield chunks of size `chunk_size`.
		Optionally limit output to `amount` bytes.
	"""

	if amount is None:
		return simple_file_iter(fr, chunk_size)
	else:
		return limited_file_iter(fr, amount, chunk_size)

def blockfileiter(path, mode="rb", encoding=None, errors=None, amount=None, chunk_size=FILE_IO_BUFFER_SIZE):
	# type: (Path, str, Optional[str], Optional[int], int) -> Iterator

	""" Iterate over file at `path` and yield chunks of size `chunk_size`.
		Optionally limit output to `amount` bytes.
	"""

	assert (mode == "rt" and encoding) or (mode == "rb" and not encoding and not errors)
	with open(path, mode, encoding=encoding, errors=errors) as fr:
		for data in iterfilelike(fr, amount, chunk_size):
			yield data

def bufferedfileiter(path, chunk_size, mode="rb", encoding=None, errors=None, amount=None, buffer_size=FILE_IO_BUFFER_SIZE):
	# type: (Path, int, str, Optional[str], Optional[int], int) -> Iterator

	""" Iterate over file at `path` reading chunks of size `buffer_size` at a time.
		Yields data chunks of `chunk_size` and optionally limits output to `amount` bytes.
	"""

	return resizer(blockfileiter(path, mode, encoding, errors, amount, buffer_size), chunk_size)

def byte_out(path, buffer_size=FILE_IO_BUFFER_SIZE):
	# type: (str, int) -> Iterator[bytes]
	""" open file and return it byte by byte """

	return resizer(blockfileiter(path, mode="rb", chunk_size=buffer_size), 1)

def consume_file(filename, buffer_size=FILE_IO_BUFFER_SIZE):
	# type: (str, int) -> None
	""" reads whole file but ignores content """

	consume(blockfileiter(filename, mode="rb", chunk_size=buffer_size))

# was: same_files, textfile_equal: equal_files(*paths, mode="rt")
def equal_files(*paths, **kwargs):
	# type: (*str, str, int) -> bool

	""" Check if files at `*paths` are equal. Chunks of size `chunk_size` are read at a time.
		Data can be optionally limited to `amount`.
	"""

	# python2 fix for 'equal_files(*paths, mode="rb", encoding=None, errors=None, amount=None, chunk_size=FILE_IO_BUFFER_SIZE)'
	mode = kwargs.pop("mode", "rb")
	encoding = kwargs.pop("encoding", None)
	errors = kwargs.pop("errors", None)
	amount = kwargs.pop("amount", None)
	chunk_size = kwargs.pop("chunk_size", FILE_IO_BUFFER_SIZE)
	assert not kwargs, "Invalid keyword arguments"

	its = tuple(blockfileiter(path, mode=mode, encoding=encoding, errors=errors, amount=amount, chunk_size=chunk_size) for path in paths)
	return iter_equal(*its)

def is_all_byte(fr, thebyte=b"\0", chunk_size=FILE_IO_BUFFER_SIZE):
	# type: (IO, bytes, int) -> bool

	""" Test if file-like `fr` consists only of `thebyte` bytes. """

	assert isinstance(thebyte, bytes)

	thebyte = thebyte*chunk_size
	for data in simple_file_iter(fr, chunk_size):
		if data != thebyte[:len(data)]:
			return False
	return True

# is this still needed?
def file_byte_reader(filename, inputblocksize, outputblocksize, DEBUG=True):
	assert (inputblocksize % outputblocksize == 0) or (outputblocksize % inputblocksize == 0), "Neither input nor output size is a multiple of the other"

	bytes_yielded = 0
	bytes = bytearray(max(inputblocksize, outputblocksize))
	bytes_used = 0
	for read in blockfileiter(filename, chunk_size=inputblocksize):
		bytes[bytes_used:bytes_used+len(read)] = read
		#print("read {} bytes to pos [{}:{}]".format(len(read),bytes_used,bytes_used+len(read)))
		bytes_used += len(read)
		pos = 0
		while bytes_used >= outputblocksize:
			yield bytes[pos:pos+outputblocksize]
			bytes_yielded += outputblocksize
			#print("yielded {} bytes from pos [{}:{}]".format(outputblocksize,pos,pos+outputblocksize))
			pos += outputblocksize
			bytes_used -= outputblocksize
	if DEBUG:
		import os.path
		filesize = os.path.getsize(filename)
		if filesize != bytes_yielded:
			print("{} bytes yielded, filesize: {}".format(bytes_yielded, filesize))
