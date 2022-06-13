from __future__ import generator_stop

from genutility.test import MyTestCase, parametrize
from genutility.tree import SequenceTree


class SequenceTreeTest(MyTestCase):
    def setUp(self):
        self.tree = SequenceTree()

    def test_setgetitem(self):

        init = {
            (1,): 1,
            (1, 2): 2,
            (1, 2, 3): 3,
            (1, 1, 4): 4,
        }

        for k, v in init.items():
            self.tree[k] = v

        for key, truth in init.items():
            result = self.tree[key]
            self.assertEqual(truth, result)

        with self.assertRaises(KeyError):
            self.tree[(1, 1)]

        with self.assertRaises(KeyError):
            self.tree[(1, 3)]

    def test_contains(self):
        init = {
            (1,): 1,
            (1, 2): 2,
            (1, 2, 3): 3,
            (1, 1, 4): 4,
        }

        for k, v in init.items():
            self.tree[k] = v

        self.assertEqual(True, (1,) in self.tree)
        self.assertEqual(True, (1, 2) in self.tree)
        self.assertEqual(True, (1, 2, 3) in self.tree)
        self.assertEqual(False, (1, 1) in self.tree)
        self.assertEqual(False, (2,) in self.tree)

    def test_longest_prefix(self):
        init = {
            (1,): 1,
            (1, 2): 2,
            (1, 2, 3): 3,
            (1, 1, 4): 4,
        }

        for k, v in init.items():
            self.tree[k] = v

        self.assertEqual([], self.tree.longest_prefix([3], False)[0])
        self.assertEqual(([1, 2], 2), self.tree.longest_prefix([1, 2], True))
        self.assertEqual(([1, 2], 2), self.tree.longest_prefix([1, 2, 4], True))

    def test_get_node(self):
        init = {
            (1,): 1,
            (1, 2): 2,
            (1, 2, 3): 3,
            (1, 1, 4): 4,
        }

        for k, v in init.items():
            self.tree[k] = v

        self.assertEqual({"_": 2, 3: {"_": 3}}, self.tree.get_node([1, 2]))
        self.assertEqual({"_": 3}, self.tree.get_node([1, 2, 3]))
        self.assertEqual({4: {"_": 4}}, self.tree.get_node([1, 1]))
        with self.assertRaises(KeyError):
            self.tree.get_node([2])

    def test_pop(self):
        key = (1,)
        self.tree[key] = 1

        self.assertEqual(1, self.tree.pop(key))
        with self.assertRaises(KeyError):
            self.tree.pop(key)

    def test_popdefault(self):
        key = (1,)
        self.tree[key] = 1

        self.assertEqual(1, self.tree.popdefault(key, None))
        self.assertEqual(None, self.tree.popdefault(key, None))

    def test_popitem(self):
        key = (1,)
        self.tree[key] = 1

        self.assertEqual(((1,), 1), self.tree.popitem())

        with self.assertRaises(KeyError):
            self.tree.popitem()

    def test_clear(self):
        key = (1,)
        self.tree[key] = 1
        self.tree.clear()
        with self.assertRaises(KeyError):
            self.tree[key]

    def test_copy(self):
        init = {
            (1,): 1,
            (2,): [1],
            (1, 2): 2,
            (1, 2, 3): 3,
            (1, 1, 4): 4,
        }

        for k, v in init.items():
            self.tree[k] = v

        cpy = self.tree.copy()

        # copy should yield same data
        self.assertEqual(cpy, self.tree)

        # modifying keys should not change copy
        self.tree[(1,)] = 2
        self.assertEqual(cpy[(1,)], 1)

        # modifying values should change copy
        self.tree[(2,)][0] = 2
        self.assertEqual(cpy[(2,)][0], 2)

    def test_optimized(self):
        init = {
            (1,): 1,
            (1, 2): 2,
            (1, 2, 3): 3,
            (1, 1, 4): 4,
        }

        for k, v in init.items():
            self.tree[k] = v

        del self.tree[(1, 1, 4)]

        opt = self.tree.optimized()

        branches, leaves = self.tree.calc_branches(), self.tree.calc_leaves()
        self.assertEqual((4, 3), (branches, leaves))
        branches, leaves = opt.calc_branches(), opt.calc_leaves()
        self.assertEqual((3, 3), (branches, leaves))

    def test_calc_max_depth_empty(self):
        truth = 0
        result = self.tree.calc_max_depth()
        self.assertEqual(truth, result)

    @parametrize(((1,), 1), ((1, 2), 2), ((1, 2, 3), 3))
    def test_calc_max_depth(self, keys, truth):
        self.tree[keys] = None
        result = self.tree.calc_max_depth()
        self.assertEqual(truth, result)

    def test_calc_branches_empty(self):
        truth = 0
        result = self.tree.calc_branches()
        self.assertEqual(truth, result)

    def test_calc_branches(self):
        tree = SequenceTree.fromtree({1: {1: {1: {}, 2: {}}}, 2: {}})
        truth = 3
        result = tree.calc_branches()
        self.assertEqual(truth, result)

    def test_calc_leaves_empty(self):
        truth = 0
        result = self.tree.calc_leaves()
        self.assertEqual(truth, result)

    @parametrize(((1,), 1), ((1, 2), 2), ((1, 2, 3), 3), ((1, 2, 3), 3))
    def test_calc_leaves(self, keys, truth):
        self.tree[keys] = None
        result = self.tree.calc_leaves()
        self.assertEqual(truth, result)

    def test_values_empty(self):
        truth = []
        result = list(self.tree.values())
        self.assertUnorderedSeqEqual(truth, result)

    @parametrize(
        ((1,), "a", ["a"]),
        ((1, 2), "b", ["a", "b"]),
        ((1, 2, 3), "c", ["a", "b", "c"]),
        ((1, 2, 3), "d", ["a", "b", "d"]),
    )
    def test_values(self, keys, val, truth):
        self.tree[keys] = val
        result = list(self.tree.values())
        self.assertUnorderedSeqEqual(truth, result)

    def test_keys_empty(self):
        truth = []
        result = list(self.tree.keys())
        self.assertUnorderedSeqEqual(truth, result)

    @parametrize(
        ((1,), [(1,)]),
        ((1, 2), [(1,), (1, 2)]),
        ((1, 2, 3), [(1,), (1, 2), (1, 2, 3)]),
    )
    def test_keys(self, keys, truth):
        self.tree[keys] = None
        result = list(self.tree.keys())
        self.assertUnorderedSeqEqual(truth, result)

    def test_items_empty(self):
        truth = []
        result = list(self.tree.items())
        self.assertUnorderedSeqEqual(truth, result)

    @parametrize(
        ((1,), "a", [((1,), "a")]),
        ((1, 2), "b", [((1,), "a"), ((1, 2), "b")]),
        ((1, 2, 3), "c", [((1,), "a"), ((1, 2), "b"), ((1, 2, 3), "c")]),
        ((1, 2, 3), "d", [((1,), "a"), ((1, 2), "b"), ((1, 2, 3), "d")]),
    )
    def test_items(self, keys, val, truth):
        self.tree[keys] = val
        result = list(self.tree.items())
        self.assertUnorderedSeqEqual(truth, result)


if __name__ == "__main__":
    import unittest

    unittest.main()
