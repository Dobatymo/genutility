from __future__ import absolute_import, division, print_function, unicode_literals

from future.utils import viewitems, viewvalues

from operator import itemgetter
from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
	from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional, Set, Tuple, TypeVar
	T = TypeVar("T")

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

		from Levenshtein import distance # pip install python-Levenshtein

		words = ["laptop", "security", "microsoft", "computer", "software", "tree", "algorithm", "desktop"]

		tree = BKTree(distance)
		tree.update(words)
		tree.saveimage("bk-tree.gv")
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

class RoutingObject(object):

	def __init__(self, value):
		# type: (T, ) -> None

		self.value = value

		self.subtree = None # type: Optional[NodeType]
		self.distance_to_parent = None # type: Optional[float]
		self.covering_radius = None # type: Optional[float]

	def __repr__(self):
		return "RoutingObject({}, radius={}, tree={})".format(self.value, self.covering_radius, self.subtree)

	def set_subtree(self, node):
		self.subtree = node
		node.parent_object = self

class LeafObject(object):

	def __init__(self, value):
		# type: (T, ) -> None

		self.value = value

		self.distance_to_parent = None # type: Optional[float]

	def __repr__(self):
		return "LeafObject({})".format(self.value)

	def to_routing_object(self):
		return RoutingObject(self.value)

def isid(obj):
	if obj is None:
		return None
	else:
		return id(obj)

class MNode(object):

	maxsize = 4

	def __init__(self, distance_func, parent_node, parent_object):
		# type: (Callable, Optional[NodeType], Optional[ObjectType]) -> None

		self.distance_func = distance_func
		self.parent_node = parent_node
		self.parent_object = parent_object

	@property
	def is_root(self):
		# type: () -> bool

		return self.parent_node is None

	@property
	def is_full(self):
		# type: () -> bool

		return len(self.objects) >= self.maxsize

	def add(self, object):
		# type: (ObjectType, ) -> None

		self.objects.add(object)
		if isinstance(object, RoutingObject):
			object.subtree.parent_node = self

		if not self.is_root:
			object.distance_to_parent = self.distance_func(object.value, self.parent_object.value)

	def replace(self, o1, o2):
		# type: (ObjectType, ObjectType) -> None

		self.objects.remove(o1)
		self.objects.add(o2)

	def __repr__(self):
		return repr({
			"parent_node": isid(self.parent_node),
			"parent_object": isid(self.parent_object),
			"objects": self.objects,
		})

class InternalNode(MNode):

	def __init__(self, distance_func, parent_node, parent_object):
		# type: (Callable, Optional[NodeType], Optional[ObjectType]) -> None

		MNode.__init__(self, distance_func, parent_node, parent_object)
		self.objects = set() # type: Set[RoutingObject]

	def set_objects(self, objects):
		# type: (Set[RoutingObject], ) -> None

		self.objects = objects
		op = self.parent_object

		for o in objects:
			assert o.subtree.parent_object is o
			o.subtree.parent_node = self

		if not self.is_root:
			for o in objects:
				o.distance_to_parent = self.distance_func(op.value, o.value)

			if objects:
				op.covering_radius = max(o.distance_to_parent + o.covering_radius for o in objects)
			else:
				op.covering_radius = 0

	def update_objects(self):
		for o in self.objects:
			assert o.subtree.parent_object is o
			assert o.subtree.parent_node is self

		if not self.is_root:
			op = self.parent_object

			for o in self.objects:
				o.distance_to_parent = self.distance_func(op.value, o.value)

			op.covering_radius = max(o.distance_to_parent + o.covering_radius for o in self.objects)

class LeafNode(MNode):

	def __init__(self, distance_func, parent_node, parent_object):
		# type: (Callable, Optional[NodeType], Optional[ObjectType]) -> None

		MNode.__init__(self, distance_func, parent_node, parent_object)
		self.objects = set() # type: Set[LeafObject]

	def set_objects(self, objects):
		# type: (Set[LeafObject], ) -> None

		self.objects = objects
		op = self.parent_object

		if not self.is_root:
			for o in objects:
				o.distance_to_parent = self.distance_func(op.value, o.value)

			if objects:
				op.covering_radius = max(o.distance_to_parent for o in objects)
			else:
				op.covering_radius = 0

	def update_objects(self):
		if not self.is_root:
			op = self.parent_object

			for o in self.objects:
				o.distance_to_parent = self.distance_func(op.value, o.value)

			op.covering_radius = max(o.distance_to_parent for o in self.objects)

ObjectType = Union[RoutingObject, LeafObject]
NodeType = Union[InternalNode, LeafNode]

from random import sample


def _promote_random(distance_func, objects):
	# type: (Callable, Set[ObjectType]) -> Tuple[ObjectType, ObjectType]

	a, b = sample(objects, 2)
	return a, b

def _partition_generalized_hyperplane(distance_func, objects, o1, o2):
	# type: (Callable, Set[ObjectType], ObjectType, ObjectType) -> Tuple[Set[ObjectType], Set[ObjectType]]

	a = set() # type: Set[ObjectType]
	b = set() # type: Set[ObjectType]

	for o in objects:
		d1 = distance_func(o.value, o1.value)
		d2 = distance_func(o.value, o2.value)

		if d1 <= d2:
			a.add(o)
		else:
			b.add(o)

	return a, b

class MTree(object):

	""" See: M-tree: An Efficient Access Method for Similarity Search in Metric Spaces (1997)
	"""

	def __init__(self, distance_func, promote=None, partition=None, does_not_work_yet=None):
		# type: (Callable, Optional[str], Optional[str]) -> None

		if does_not_work_yet != "OK":
			raise RuntimeError("MTree is work in progress")

		self.distance_func = distance_func

		self.root = LeafNode(self.distance_func, None, None)

		self._promote = {
			"random": _promote_random,
		}[promote or "random"]
		self._partition = {
			"generalized-hyperplane": _partition_generalized_hyperplane,
		}[partition or "generalized-hyperplane"]

	def __repr__(self):
		return "<MTree: {!r}>".format(self.root)

	def _keys(self, node):
		if isinstance(node, InternalNode):
			for ro in node.objects:
				for value in self._keys(ro.subtree):
					yield value
		else:
			for lo in node.objects:
				yield lo.value

	def _split(self, node, object):
		# type: (NodeType, ObjectType) -> None

		#if not node.is_root:
		op = node.parent_object
		np = node.parent_node

		n_new = type(node)(self.distance_func, np, op)  # same type like existing
		all_objects = node.objects | {object}
		o1, o2 = self._promote(self.distance_func, all_objects)
		os1, os2 = self._partition(self.distance_func, all_objects, o1, o2)

		if isinstance(node, LeafNode):
			o1 = o1.to_routing_object()
			o2 = o2.to_routing_object()

		o1.set_subtree(node)
		o2.set_subtree(n_new)

		if node.is_root:
			# print("is_root")
			self.root = InternalNode(self.distance_func, None, None)
			self.root.add(o1)
			self.root.add(o2)

			node.set_objects(os1) # recalculates distances
			n_new.set_objects(os2)

		else:
			np.replace(op, o1)
			if np.is_full:
				# print("is_full")
				self._split(np, o2)
			else:
				# print("is not full")
				np.add(o2)
				np.update_objects()

	def _add(self, node, object):
		# type: (NodeType, LeafObject) -> None

		if not isinstance(node, LeafNode):
			#print("not leaf", node)
			distances = [self.distance_func(ro.value, object.value) for ro in node.objects]

			n_in = [(ro, d) for ro, d in zip(node.objects, distances) if d <= ro.covering_radius]
			if n_in:
				found = min(n_in, key=itemgetter(1))[0]
			else:
				it = ((ro, d - ro.covering_radius, d) for ro, d in zip(node.objects, distances))
				min_entry = min(it, key=itemgetter(1))
				found = min_entry[0]
				found.covering_radius = min_entry[2]

			self._add(found.subtree, object)
		else:
			if not node.is_full:
				#print("not full", "LeafNode", node)
				node.add(object)
			else:
				#print("is full", "LeafNode", node)
				self._split(node, object)

	def _find(self, node, value, radius):

		assert not node.is_root

		distance_parent_to_value = self.distance_func(node.parent_object.value, value)

		if not isinstance(node, LeafNode):
			for ro in node.objects:
				if abs(distance_parent_to_value - ro.distance_to_parent) <= radius + ro.covering_radius:
					if self.distance_func(ro.value, value) <= radius + ro.covering_radius:
						for value in self._find(ro.subtree, value, radius):
							yield value
		else:
			for lo in node.objects:
				if abs(distance_parent_to_value - lo.distance_to_parent) <= radius:
					if self.distance_func(lo.value, value) <= radius:
						yield lo.value

	def keys(self):
		for value in self._keys(self.root):
			yield value

	def add(self, value):
		# type: (T, ) -> None

		self._add(self.root, LeafObject(value))

	def find(self, value, radius):
		# type: (T, float) -> Iterator[T]

		node = self.root

		if not isinstance(node, LeafNode):
			for ro in node.objects:
				if self.distance_func(ro.value, value) <= radius + ro.covering_radius:
					for value in self._find(ro.subtree, value, radius):
						yield value
		else:
			for lo in node.objects:
				if self.distance_func(lo.value, value) <= radius:
					yield lo.value

def len_dist(s1, s2):
	return abs(len(s1) - len(s2))

def vals(start, end):
	# type: (int, int) -> Set[str]

	return set(str(i)*i for i in range(start, end+1))

from unittest import TestCase


class MTreeTests(TestCase):

	def test_mtree_one_layer(self):
		values = vals(1, 4)

		mt = MTree(len_dist, does_not_work_yet="OK")
		for i in values:
			mt.add(i)

		assert set(mt.find("333", 1)) == vals(2, 4)
		assert set(mt.keys()) == values

	def test_mtree_two_layer(self):
		values = vals(1, 5)

		mt = MTree(len_dist, does_not_work_yet="OK")
		for i in values:
			mt.add(i)

		assert set(mt.keys()) == values

	def test_mtree_three_layer(self):
		values = vals(1, 9)

		mt = MTree(len_dist, does_not_work_yet="OK")
		for i in values:
			mt.add(i)

		assert set(mt.find("333", 1)) == vals(2, 4)
		assert set(mt.keys()) == values

if __name__ == "__main__":

	import unittest
	unittest.main()
