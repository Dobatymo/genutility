from __future__ import absolute_import, division, print_function, unicode_literals

from future.utils import viewitems, viewvalues

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
	from typing import Any, Callable, Dict, List, Iterator, Iterable, Optional, Set, Tuple
	from graphviz import Digraph

if __debug__:
	import graphviz

class BKNode(object):

	__slots__ = ["value", "leaves"]

	def __init__(self, value, leaves):
		# type: (Any, Dict[Any, BKNode]) -> None

		self.value = value
		self.leaves = leaves

	def __str__(self):
		return str(self.value) + ": " + str(self.leaves)

	def __repr__(self):
		return repr(self.value) + ": " + repr(self.leaves)

class BKTree(object):

	""" BK-tree. Used for nearest neighbor queries according to a discrete metric.
		Examples for the metric are the Manhattan distance or the Levenshtein distance.
	"""

	def __init__(self, distance_func):
		# type: (Callable[[Any, Any], int], ) -> None

		self.distance_func = distance_func
		self.root = None # type: Optional[BKNode]

	def add(self, value):
		# type: (Any, ) -> None

		if self.root is None:
			self.root = BKNode(value, {})
			return

		node = self.root
		while True:
			distance = self.distance_func(value, node.value)
			try:
				node = node.leaves[distance]
			except KeyError:
				node.leaves[distance] = BKNode(value, {})
				break

	def update(self, values):
		# type: (Iterable[Any], ) -> None

		for value in values:
			self.add(value)

	def find(self, value, max_distance):
		# type: (Any, int) -> List[Tuple[int, Any]]

		""" Returns all values from tree where the metric distance
			is less or equal to `max_distance`.
		"""

		node = self.root
		ret = [] # type: List[Tuple[int, Any]]

		if node is None:
			return ret

		candidates = [node] # is a deque better here?

		while candidates:
			candidate = candidates.pop()
			distance = self.distance_func(value, candidate.value)

			if distance <= max_distance:
				ret.append((distance, candidate.value))

			# instead of looking for candidates by searching,
			# one could also directly access the necessary keys in the dict
			for d, bknode in viewitems(candidate.leaves):
				lower = distance - max_distance
				upper = distance + max_distance
				if lower <= d <= upper:
					candidates.append(bknode)

		return ret

	@staticmethod
	def _find_by_distance(node, distance):
		# type: (BKNode, int) -> Iterator[Set[Any]]

		for d, bknode in viewitems(node.leaves):
			if d == distance:
				nodeset = set(BKTree._values(bknode))
				nodeset.add(node.value)
				yield nodeset
			for ret in BKTree._find_by_distance(bknode, distance):
				yield ret

	def find_by_distance(self, distance):
		# type: (int, ) -> Iterator[Set[Any]]

		""" Find all sets of values base on `distance` between each other.
		"""

		if self.root is None:
			return iter([])
		else:
			return BKTree._find_by_distance(self.root, distance)

	@staticmethod
	def _dot(dot, node):
		# type: (Digraph, BKNode) -> None

		for distance, childnode in viewitems(node.leaves):
			dot.node(str(childnode.value))
			dot.edge(str(node.value), str(childnode.value), label=str(distance))
			BKTree._dot(dot, childnode)

	def saveimage(self, filename, format="png"):
		from graphviz import Digraph

		if self.root is None:
			raise ValueError("Tree is empty")

		dot = Digraph(format=format)
		dot.node(str(self.root.value))
		self._dot(dot, self.root)
		dot.render(filename)

	@staticmethod
	def _values(node):
		# type: (BKNode, ) -> Iterator[Any]

		yield node.value
		for leaf in viewvalues(node.leaves):
			for value in BKTree._values(leaf):
				yield value

	def values(self):
		# type: () -> Iterator[Any]

		if self.root is None:
			return iter([])
		else:
			return self._values(self.root)

	def __iter__(self):
		# type: () -> Iterator[Any]

		return self.values()

if __name__ == "__main__":
	from Levenshtein import distance as levenshtein_distance # pip install python-Levenshtein
	#from leven import levenshtein as levenshtein_distance # pip install leven

	from argparse import ArgumentParser
	parser = ArgumentParser()
	parser.add_argument("outpath", default="bk-tree.gv", nargs="?")
	args = parser.parse_args()

	words = ["laptop", "security", "microsoft", "computer", "software", "tree", "algorithm", "desktop"]

	tree = BKTree(levenshtein_distance)
	tree.update(words)
	tree.saveimage(args.outpath)
