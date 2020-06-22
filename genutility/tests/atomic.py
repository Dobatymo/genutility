from __future__ import absolute_import, division, print_function, unicode_literals

from genutility.test import MyTestCase, parametrize
from genutility.atomic import TransactionalCreateFile

class AtomicTest(MyTestCase):

	def test_TransactionalCreateFile(self):

		path = "testtemp/TransactionalCreateFile.txt"
		values = ["asd", "qwe"]

		with TransactionalCreateFile(path, "wt", encoding="utf-8") as fw:
			for value in values:
				fw.write(value)

		with open(path, "rt", encoding="utf-8") as fr:
			result = fr.read()

		self.assertEqual("".join(values), result)

if __name__ == "__main__":
	import unittest
	unittest.main()
