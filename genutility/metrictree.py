from operator import itemgetter
from typing import Callable, Iterator, Optional, Set, Tuple, TypeVar, Union

T = TypeVar("T")


class RoutingObject:
    def __init__(self, value: T) -> None:
        self.value = value

        self.subtree: Optional["NodeType"] = None
        self.distance_to_parent: Optional[float] = None
        self.covering_radius: Optional[float] = None

    def __repr__(self) -> str:
        return f"RoutingObject({self.value}, radius={self.covering_radius}, tree={self.subtree})"

    def set_subtree(self, node) -> None:
        self.subtree = node
        node.parent_object = self


class LeafObject:
    def __init__(self, value: T) -> None:
        self.value = value

        self.distance_to_parent: Optional[float] = None

    def __repr__(self):
        return f"LeafObject({self.value})"

    def to_routing_object(self):
        return RoutingObject(self.value)


def isid(obj):
    if obj is None:
        return None
    else:
        return id(obj)


class MNode:
    maxsize = 4

    def __init__(
        self, distance_func: Callable, parent_node: Optional["NodeType"], parent_object: Optional["ObjectType"]
    ) -> None:
        self.distance_func = distance_func
        self.parent_node = parent_node
        self.parent_object = parent_object

    @property
    def is_root(self) -> bool:
        return self.parent_node is None

    @property
    def is_full(self) -> bool:
        return len(self.objects) >= self.maxsize

    def add(self, obj: "ObjectType") -> None:
        self.objects.add(obj)
        if isinstance(obj, RoutingObject):
            obj.subtree.parent_node = self

        if not self.is_root:
            obj.distance_to_parent = self.distance_func(obj.value, self.parent_object.value)

    def replace(self, o1: "ObjectType", o2: "ObjectType") -> None:
        self.objects.remove(o1)
        self.objects.add(o2)

    def __repr__(self):
        return repr(
            {
                "parent_node": isid(self.parent_node),
                "parent_object": isid(self.parent_object),
                "objects": self.objects,
            }
        )


class InternalNode(MNode):
    def __init__(
        self, distance_func: Callable, parent_node: Optional["NodeType"], parent_object: Optional["ObjectType"]
    ) -> None:
        MNode.__init__(self, distance_func, parent_node, parent_object)
        self.objects: Set[RoutingObject] = set()

    def set_objects(self, objects: Set[RoutingObject]) -> None:
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
    def __init__(
        self, distance_func: Callable, parent_node: Optional["NodeType"], parent_object: Optional["ObjectType"]
    ) -> None:
        MNode.__init__(self, distance_func, parent_node, parent_object)
        self.objects: Set[LeafObject] = set()

    def set_objects(self, objects: Set[LeafObject]) -> None:
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


def _promote_random(distance_func: Callable, objects: Set[ObjectType]) -> Tuple[ObjectType, ObjectType]:
    a, b = sample(objects, 2)
    return a, b


def _partition_generalized_hyperplane(
    distance_func: Callable, objects: Set[ObjectType], o1: ObjectType, o2: ObjectType
) -> Tuple[Set[ObjectType], Set[ObjectType]]:
    a: Set[ObjectType] = set()
    b: Set[ObjectType] = set()

    for o in objects:
        d1 = distance_func(o.value, o1.value)
        d2 = distance_func(o.value, o2.value)

        if d1 <= d2:
            a.add(o)
        else:
            b.add(o)

    return a, b


class MTree:
    """See: M-tree: An Efficient Access Method for Similarity Search in Metric Spaces (1997)"""

    def __init__(
        self,
        distance_func: Callable[[ObjectType, ObjectType], float],
        promote: Optional[str] = None,
        partition: Optional[str] = None,
        does_not_work_yet: Optional[str] = None,
    ) -> None:
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
        return f"<MTree: {self.root!r}>"

    def _keys(self, node):
        if isinstance(node, InternalNode):
            for ro in node.objects:
                yield from self._keys(ro.subtree)
        else:
            for lo in node.objects:
                yield lo.value

    def _split(self, node: NodeType, obj: ObjectType) -> None:
        # if not node.is_root:
        op = node.parent_object
        np = node.parent_node

        n_new = type(node)(self.distance_func, np, op)  # same type like existing
        all_objects = node.objects | {obj}
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

            node.set_objects(os1)  # recalculates distances
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

    def _add(self, node: NodeType, obj: LeafObject) -> None:
        if not isinstance(node, LeafNode):
            # print("not leaf", node)
            distances = [self.distance_func(ro.value, obj.value) for ro in node.objects]

            n_in = [(ro, d) for ro, d in zip(node.objects, distances) if d <= ro.covering_radius]
            if n_in:
                found = min(n_in, key=itemgetter(1))[0]
            else:
                it = ((ro, d - ro.covering_radius, d) for ro, d in zip(node.objects, distances))
                min_entry = min(it, key=itemgetter(1))
                found = min_entry[0]
                found.covering_radius = min_entry[2]

            self._add(found.subtree, obj)
        else:
            if not node.is_full:
                # print("not full", "LeafNode", node)
                node.add(obj)
            else:
                # print("is full", "LeafNode", node)
                self._split(node, obj)

    def _find(self, node, value, radius):
        assert not node.is_root

        distance_parent_to_value = self.distance_func(node.parent_object.value, value)

        if not isinstance(node, LeafNode):
            for ro in node.objects:
                if abs(distance_parent_to_value - ro.distance_to_parent) <= radius + ro.covering_radius:
                    if self.distance_func(ro.value, value) <= radius + ro.covering_radius:
                        yield from self._find(ro.subtree, value, radius)
        else:
            for lo in node.objects:
                if abs(distance_parent_to_value - lo.distance_to_parent) <= radius:
                    if self.distance_func(lo.value, value) <= radius:
                        yield lo.value

    def keys(self):
        yield from self._keys(self.root)

    def add(self, value: T) -> None:
        self._add(self.root, LeafObject(value))

    def find(self, value: T, radius: float) -> Iterator[T]:
        node = self.root

        if not isinstance(node, LeafNode):
            for ro in node.objects:
                if self.distance_func(ro.value, value) <= radius + ro.covering_radius:
                    yield from self._find(ro.subtree, value, radius)
        else:
            for lo in node.objects:
                if self.distance_func(lo.value, value) <= radius:
                    yield lo.value


def len_dist(s1, s2):
    return abs(len(s1) - len(s2))


def vals(start: int, end: int) -> Set[str]:
    return {str(i) * i for i in range(start, end + 1)}


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
