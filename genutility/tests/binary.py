from __future__ import absolute_import, division, print_function, unicode_literals

from future.utils import PY2
from genutility.test import MyTestCase, parametrize
from genutility.binary import encode_binary, decode_binary

if PY2:
	bytes = bytearray

class BinaryTest(MyTestCase):

	@parametrize(
		("1111111100000001", "0", bytes(b"\xff\x01")),
		([True]*8+[False]*7+[True], "0", bytes(b"\xff\x01")),
		("111111111", "0", bytes(b"\xff\x80")),
		("111111111", "1", bytes(b"\xff\xff")),
	)
	def test_encode_binary(self, it, pad, truth):
		result = encode_binary(it, pad)
		self.assertEqual(truth, result)

	@parametrize(
		(bytes(b"\xff\x01"), True, "1111111100000001"),
		(bytes(b"\xff\x01"), False, [True]*8+[False]*7+[True]),
	)
	def test_decode_binary(self, it, tostring, truth):
		result = decode_binary(it, tostring)
		self.assertIterEqual(truth, result)

if __name__ == "__main__":
	import unittest
	unittest.main()
