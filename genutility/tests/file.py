from __future__ import absolute_import, division, print_function, unicode_literals

from genutility.test import MyTestCase, parametrize
from genutility.file import equal_files, is_all_byte

class FileTest(MyTestCase):

	@parametrize(
		(("testfiles/file_1.bin", "testfiles/file_2.bin"), "rb", None, True),
		(("testfiles/file_1.bin", "testfiles/file_2.bin", "testfiles/file_3.bin"), "rb", None, True),
		(("testfiles/file_win.bin", "testfiles/file_unix.bin"), "rb", None, False),
		(("testfiles/file_win.bin", "testfiles/file_unix.bin"), "rt", 'utf-8', True)
	)
	def test_equal_files(self, files, mode, encoding, truth):
		result = equal_files(*files, mode=mode, encoding=encoding)
		self.assertEqual(truth, result)

	@parametrize(
		("testfiles/file_zeros.bin", True),
		("testfiles/file_nonzero.bin", False),
	)
	def test_is_all_byte(self, path, truth):
		with open(path, "rb") as fr:
			result = is_all_byte(fr, b"\0")
			self.assertEqual(truth, result)

if __name__ == "__main__":
	import unittest

	from genutility.file import write_file

	data = b"abcdefghijklmnopqrstuvwxyz"
	write_file(data, "testfiles/file_1.bin", "wb")
	write_file(data, "testfiles/file_2.bin", "wb")
	write_file(data, "testfiles/file_3.bin", "wb")

	data_win = b"abc\r\ndef\r\n"
	write_file(data_win, "testfiles/file_win.bin", "wb")
	data_unix = b"abc\ndef\n"
	write_file(data_unix, "testfiles/file_unix.bin", "wb")

	write_file(b"\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0", "testfiles/file_zeros.bin", "wb")
	write_file(b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f", "testfiles/file_nonzero.bin", "wb")

	unittest.main()
