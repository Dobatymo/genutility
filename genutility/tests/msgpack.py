from __future__ import absolute_import, division, print_function, unicode_literals

from genutility.test import MyTestCase, parametrize
from genutility.datetime import now
from genutility.msgpack import dumps, loads

class MsgpackTest(MyTestCase):

	@parametrize(
		({
			"int": 43,
			"float": 13.37,
			"unicode": "你好",
			"bytes": b"asd",
			"datetime": now(),
			"set": {1, 2, 3},
			"frozenset": frozenset({1, 2, 3}),
		},)
	)
	def test_dumps_loads(self, truth):
		result = loads(dumps(truth))
		self.assertEqual(truth, result)

if __name__ == "__main__":
	import unittest
	unittest.main()
