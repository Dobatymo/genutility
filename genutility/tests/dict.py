from __future__ import generator_stop

from genutility.dict import keydefaultdict, mapmap, subdict, subdictdefault
from genutility.test import MyTestCase, parametrize


class DictTest(MyTestCase):

	@parametrize(
		({1:"a", 2:"b", 3:"c"}, (1, 2, 3), ("a", "b", "c")),
	)
	def test_mapmap(self, d, it, truth):
		result = mapmap(d, it)
		self.assertIterEqual(result, truth)

	@parametrize(
		({}, (), {}),
		({1:2, 3:4, 5:6}, (), {}),
		({1:2, 3:4, 5:6}, (1, 3, 5), {1:2, 3:4, 5:6}),
	)
	def test_subdict(self, d, it, truth):
		result = subdict(d, it)
		self.assertEqual(truth, result)

	@parametrize(
		({}, (1, 3, 5), {}),
	)
	def test_subdict_error(self, d, it, truth):
		with self.assertRaises(KeyError):
			subdict(d, it)

	@parametrize(
		({}, (), None, {}),
		({1:2, 3:4, 5:6}, (), None, {}),
		({1:2, 3:4, 5:6}, (1, 3, 5), None, {1:2, 3:4, 5:6}),
		({}, (1, 3, 5), None, {1: None, 3: None, 5:None}),
	)
	def test_subdictdefault(self, d, it, default, truth):
		result = subdictdefault(d, it, default)
		self.assertEqual(truth, result)

	@parametrize(
		(lambda x: x, "test", "test"),
		(lambda x: x*2, 1, 2),
	)
	def test_keydefaultdict(self, func, key, truth):
		d = keydefaultdict(func)
		self.assertEqual(truth, d[key])

	def test_keydefaultdict_error(self):
		d = keydefaultdict()
		with self.assertRaises(KeyError):
			d["test"]

if __name__ == "__main__":
	import unittest
	unittest.main()
