from __future__ import generator_stop

from unittest import SkipTest

from genutility.math import number_metric
from genutility.metrictree import BKTree
from genutility.test import MyTestCase, parametrize


class BKTreeTest(MyTestCase):

	def test_range(self):
		value = range(10)

		tree = BKTree(number_metric)
		tree.update(value)
		truth = list(value)

		self.assertEqual(list(tree), truth)

	def test_words(self):
		try:
			from Levenshtein import distance as levenshtein_distance
			from nltk.corpus import words
		except ImportError:
			raise SkipTest("Missing imports. pip install python-Levenshtein nltk")

		maxdistance = 2
		words = words.words()

		def find_closest(word, results):
			return sorted((levenshtein_distance(word, w), w) for w in words)[:results]

		tree = BKTree(levenshtein_distance)
		tree.update(words)

		for word in ["asdqwe", "abbaration", "illegitimate", "penourius"]:

			results = sorted(tree.find(word, maxdistance)) # bktree
			truth = find_closest(word, len(results)) # linear search

			self.assertEqual(results, truth)

if __name__ == "__main__":
	import unittest
	unittest.main()
