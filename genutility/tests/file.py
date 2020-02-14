from __future__ import absolute_import, division, print_function, unicode_literals

import os, tempfile, os.path

from genutility.test import MyTestCase, parametrize
from genutility.file import write_file # not tested, used to set up the tests
from genutility.file import equal_files, is_all_byte, OpenFileAndDeleteOnError, blockfilesiter

class FileTest(MyTestCase):

	@classmethod
	def setUpClass(cls):
		data = b"abcdefghijklmnopqrstuvwxyz"
		write_file(data, "testtemp/file_1.bin", "wb")
		write_file(data, "testtemp/file_2.bin", "wb")
		write_file(data, "testtemp/file_3.bin", "wb")

		data_win = b"abc\r\ndef\r\n"
		write_file(data_win, "testtemp/file_win.bin", "wb")
		data_unix = b"abc\ndef\n"
		write_file(data_unix, "testtemp/file_unix.bin", "wb")

		write_file(b"\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0", "testtemp/file_zeros.bin", "wb")
		write_file(b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f", "testtemp/file_nonzero.bin", "wb")

	@parametrize(
		(("testtemp/file_1.bin", "testtemp/file_2.bin"), "rb", None, True),
		(("testtemp/file_1.bin", "testtemp/file_2.bin", "testtemp/file_3.bin"), "rb", None, True),
		(("testtemp/file_win.bin", "testtemp/file_unix.bin"), "rb", None, False),
		(("testtemp/file_win.bin", "testtemp/file_unix.bin"), "rt", "utf-8", True)
	)
	def test_equal_files(self, files, mode, encoding, truth):
		result = equal_files(*files, mode=mode, encoding=encoding)
		self.assertEqual(truth, result)

	@parametrize(
		("testtemp/file_zeros.bin", True),
		("testtemp/file_nonzero.bin", False),
	)
	def test_is_all_byte(self, path, truth):
		with open(path, "rb") as fr:
			result = is_all_byte(fr, b"\0")
			self.assertEqual(truth, result)

	def test_OpenFileAndDeleteOnError(self):
		path = os.path.join(tempfile.gettempdir(), "excepttest.tmp") # not super safe

		with OpenFileAndDeleteOnError(path, "wb") as fw:
			pass
		self.assertEqual(os.path.isfile(path), True)

		with self.assertRaises(RuntimeError):
			with OpenFileAndDeleteOnError(path, "wb") as fw:
				raise RuntimeError()
		self.assertEqual(os.path.isfile(path), False)

	def test_blockfilesiter(self):
		base = "testfiles/chunks"
		paths = sorted(e.path for e in os.scandir(base))

		result = blockfilesiter(paths, 2)
		truth = [b'12', b'34', b'56', b'78', b'90', b'12', b'34', b'56', b'78', b'9']
		self.assertIterEqual(truth, result)

		result = blockfilesiter(paths, 3)
		truth = [b'123', b'456', b'789', b'012', b'345', b'678', b'9']
		self.assertIterEqual(truth, result)

		result = blockfilesiter(paths, 4)
		truth = [b'1234', b'5678', b'9012', b'3456', b'789']
		self.assertIterEqual(truth, result)

		result = blockfilesiter(paths[:-1], 2)
		truth = [b'12', b'34', b'56', b'78', b'90', b'12', b'34', b'5']
		self.assertIterEqual(truth, result)

		result = blockfilesiter(paths[:-1], 3)
		truth = [b'123', b'456', b'789', b'012', b'345']
		self.assertIterEqual(truth, result)

		result = blockfilesiter(paths[:-1], 4)
		truth = [b'1234', b'5678', b'9012', b'345']
		self.assertIterEqual(truth, result)

		result = blockfilesiter(paths[:-1], 5)
		truth = [b'12345', b'67890', b'12345']
		self.assertIterEqual(truth, result)

if __name__ == "__main__":
	import unittest
	unittest.main()
