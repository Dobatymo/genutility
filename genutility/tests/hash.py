from __future__ import absolute_import, division, print_function, unicode_literals

from genutility.test import MyTestCase, parametrize
from genutility.hash import crc32_hash_file, sha1_hash_file, md5_hash_file, ed2k_hash_file_v1, ed2k_hash_file_v2

class HashTest(MyTestCase):

	@parametrize(
		("testfiles/hash.bin", "4c2750bd"),
	)
	def test_crc32_hash_file(self, path, truth):
		result = crc32_hash_file(path)
		self.assertEqual(truth, result)

	@parametrize(
		("testfiles/hash.bin", "32d10c7b8cf96570ca04ce37f2a19d84240d3a89"),
	)
	def test_sha1_hash_file(self, path, truth):
		result = sha1_hash_file(path).hexdigest()
		self.assertEqual(truth, result)

	@parametrize(
		("testfiles/hash.bin", "c3fcd3d76192e4007dfb496cca67e13b"),
	)
	def test_md5_hash_file(self, path, truth):
		result = md5_hash_file(path).hexdigest()
		self.assertEqual(truth, result)

class Ed2kTest(MyTestCase):

	@parametrize(
		("testfiles/hash.bin", "d79e1c308aa5bbcdeea8ed63df412da9"),
	)
	def test_hash_file_v1v2(self, path, truth):
		result = ed2k_hash_file_v1(path)
		self.assertEqual(truth, result)

		result = ed2k_hash_file_v2(path)
		self.assertEqual(truth, result)

	@parametrize(

	)
	def test_hash_file_v1(self, path, truth):
		pass

	@parametrize(

	)
	def test_hash_file_v2(self, path, truth):
		pass

if __name__ == "__main__":
	import unittest
	from genutility.file import write_file

	write_file(b"abcdefghijklmnopqrstuvwxyz", "testfiles/hash.bin", "wb")
	unittest.main()
