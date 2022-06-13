from __future__ import generator_stop

from collections.abc import Iterable, Mapping, MutableMapping
from typing import Any, Dict, Hashable, Iterator, List, Optional, Tuple, Union


class SequenceTree(MutableMapping):

    """SequenceTree is a tree class to store sequences, often called a Trie.
    It implements the MutableMapping interface, so it can be used like a dictionary.
    Compared to a dict, it offers a few advantages however:
    - common prefixes are only stored as one node
    - it supports the `longest_prefix` method
    """

    """ SequenceTree structure is not recursive, dicts are recursive.
		which way would be better? if SeqTrees were recursive, methods like values()
		would be easier to implement, but it would also incur another layer of
		abstraction which would make things slower?
	"""

    # __slots__ = ("root", "endkey")

    def __init__(self, data=None, endkey="_"):
        # type: (Optional[Union[Mapping, Iterable]], Hashable) -> None

        self.root = dict()  # type: Dict[Hashable, Any]
        self.endkey = endkey
        if data is None:
            pass
        elif isinstance(data, Mapping):  # mapping should be before Iterable
            for k, v in data.items():
                self[k] = v
        elif isinstance(data, Iterable):
            for k, v in data:
                self[k] = v
        else:
            raise ValueError("data should be a iterable or mapping")

    def iter_node(self, node) -> Iterator[Tuple[List[Any], Any]]:

        for k, v in node.items():
            if k == self.endkey:
                yield [], v
            else:
                for a, b in self.iter_node(v):
                    yield [k] + a, b

    @classmethod
    def fromtree(cls, tree, endkey="_"):
        # type: (dict, Hashable) -> SequenceTree

        seqtree = cls(endkey=endkey)
        seqtree.root = tree
        return seqtree

    def __contains__(self, keys):
        # type: (Iterable[Hashable], ) -> bool

        try:
            self[keys]
            return True
        except KeyError:
            return False

    def __getitem__(self, keys):
        # type: (Iterable[Hashable], ) -> Any

        node = self.root
        for word in keys:
            node = node[word]
        return node[self.endkey]

    def __setitem__(self, keys, value):
        # type: (Iterable[Hashable], Any) -> None

        node = self.root
        for key in keys:
            node = node.setdefault(key, dict())

        node[self.endkey] = value

    def set(self, keys, value):
        # type: (Iterable[Hashable], Any) -> bool

        """Same as `__setitem__`, except it returns `True` if the key wasn't used before."""

        node = self.root
        for word in keys:
            node = node.setdefault(word, dict())

        if self.endkey in node:
            node[self.endkey] = value
            return False
        else:
            node[self.endkey] = value
            return True

    def __delitem__(self, keys):
        # type: (Iterable[Hashable], ) -> None

        node = self.root
        for key in keys:
            node = node[key]
        del node[self.endkey]

    def _copy(self, node):
        # type: (dict, ) -> dict

        ret = dict()

        for k, v in node.items():
            if k != self.endkey:
                ret[k] = self._copy(v)
            else:
                ret[k] = v

        return ret

    def copy(self):
        # type: () -> SequenceTree

        """shallow copy"""

        tree = self._copy(self.root)
        return self.fromtree(tree, self.endkey)

    def __iter__(self):
        # type: () -> Iterator

        return iter(self.keys())

    def __eq__(self, rhs):
        # type: (object, ) -> bool

        if isinstance(rhs, SequenceTree):
            return self.root == rhs.root and self.endkey == rhs.endkey
        else:
            return False

    def __ne__(self, rhs):
        # type: (object, ) -> bool

        if isinstance(rhs, SequenceTree):
            return self.root != rhs.root or self.endkey != rhs.endkey
        else:
            return False

    def __str__(self):
        # type: () -> str

        return str(self.root)

    def __len__(self):
        raise NotImplementedError("use slower SequenceTree.calc_leaves()")

    def pop(self, keys):
        # type: (Iterable[Hashable], ) -> Any

        node = self.root
        for key in keys:
            node = node[key]
        return node.pop(self.endkey)

    def popdefault(self, keys, default=None):
        # type: (Iterable[Hashable], Optional[Any]) -> Any

        try:
            return self.pop(keys)
        except KeyError:
            return default

    """ slower, I think?
	def popitem(self):
		try:
			keys = next(self.keys())
			return keys, self.pop(keys)
		except StopIteration:
			raise KeyError("tree is empty") from None
	"""

    def _popitem(self, node, branch):
        # type: (Dict[Hashable, Any], Tuple[Hashable, ...]) -> Tuple[Tuple[Hashable, ...], Any]

        for key, value in node.items():
            if key != self.endkey:
                try:
                    ret = self._popitem(value, branch + (key,))
                    break
                except KeyError:
                    pass
            else:
                del node[key]
                ret = branch, value
                break
        else:
            raise KeyError("tree is empty") from None
        return ret

    def popitem(self):
        # type: () -> Tuple[Tuple[Hashable, ...], Any]
        """leaves empty dicts behind. thus it's not good for looping."""

        return self._popitem(self.root, ())

    def _optimized(self, node):
        # type: (Dict[Hashable, Any], ) -> Dict[Hashable, Any]

        opt = {}

        for k, v in node.items():
            if k != self.endkey:
                opt[k] = self._optimized(v)
            else:
                opt[k] = v

        return {k: v for k, v in opt.items() if v}

    def optimized(self):
        # type: () -> SequenceTree

        """Returns shallow copy with empty branches removed."""

        tree = self._optimized(self.root)
        return SequenceTree.fromtree(tree, self.endkey)

    def update(self, other):
        raise NotImplementedError("update does not work yet")

    def clear(self):
        # type: () -> None

        """Removes all leaves and branches from tree."""

        self.root.clear()

    def get(self, keys, default=None):
        # type: (Iterable[Hashable], Optional[Any]) -> Any

        try:
            return self[keys]
        except KeyError:
            return default

    def setdefault(self, keys, default=None):
        # type: (Iterable[Hashable], Optional[Any]) -> Any

        node = self.root
        for word in keys:
            node = node.setdefault(word, dict())

        return node.setdefault(self.endkey, default)

    def _values(self, node):
        # type: (Dict[Hashable, Any], ) -> Iterator[Any]

        for key, value in node.items():
            if key != self.endkey:
                yield from self._values(value)
            else:
                yield value

    def values(self):  # itervalues
        # type: () -> Iterator[Any]

        return self._values(self.root)

    def _keys(self, node, branch):
        # type: (Dict[Hashable, Any], Tuple[Hashable, ...]) -> Iterator[Tuple[Hashable, ...]]

        for key, value in node.items():
            if key != self.endkey:
                yield from self._keys(value, branch + (key,))
            else:
                yield branch

    def keys(self):  # iterkeys
        # type: () -> Iterator[Tuple[Hashable, ...]]

        return self._keys(self.root, ())

    def _items(self, node, branch):
        # type: (Dict[Hashable, Any], Tuple[Hashable, ...]) -> Iterator[Tuple[Tuple[Hashable, ...], Any]]

        for key, value in node.items():
            if key != self.endkey:
                yield from self._items(value, branch + (key,))
            else:
                yield branch, value

    def items(self):  # iteritems
        # type: () -> Iterator[Tuple[tuple, Any]]
        return self._items(self.root, ())

    # others

    def longest_prefix(self, keys, full=True):
        # type: (Iterable, bool) -> Tuple[list, Any]

        node = self.root
        ret = []
        for word in keys:
            try:
                node = node[word]
                ret.append(word)
            except KeyError:
                break
        if full:
            node = node[self.endkey]  # should this be within try-except like above? nope.
        return ret, node

    def get_node(self, keys):
        node = self.root
        for word in keys:
            node = node[word]

        return node

    @classmethod
    def _calc_max_depth(cls, node):
        # type: (dict, ) -> int

        if node:
            return max(cls._calc_max_depth(v) for v in node.values()) + 1
        else:
            return 0

    def calc_max_depth(self):
        # type: () -> int

        if self.root:
            return self._calc_max_depth(self.root) - 1
        else:
            return 0

    def _calc_branches(self, node):
        # type: (dict, ) -> int

        ret = 0

        for k, v in node.items():
            if k != self.endkey and v:
                ret += self._calc_branches(v)
            else:
                ret += 1
        return ret

    def calc_branches(self):
        # type: () -> int
        return self._calc_branches(self.root)

    def _calc_leaves(self, node):
        # type: (dict, ) -> int
        ret = 0

        for k, v in node.items():
            if k != self.endkey:
                ret += self._calc_leaves(v)
            else:
                ret += 1
        return ret

    def calc_leaves(self):
        # type: () -> int
        return self._calc_leaves(self.root)
