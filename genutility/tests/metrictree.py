from genutility.metrictree import LeafObject, MTree, len_dist, vals
from genutility.test import MyTestCase


class Node:
    pass


class MTreeTest(MyTestCase):
    def test_leaf_to_routing_object(self):
        node = Node()
        routing = LeafObject("x").to_routing_object()
        routing.set_subtree(node)

        self.assertIs(routing, node.parent_object)

    def test_mtree_one_layer(self):
        tree = MTree(len_dist, does_not_work_yet="OK")
        for value in vals(1, 4):
            tree.add(value)

        self.assertEqual(vals(1, 4), set(tree.keys()))
        self.assertEqual(vals(2, 4), set(tree.find("333", 1)))


if __name__ == "__main__":
    import unittest

    unittest.main()
