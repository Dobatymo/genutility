from __future__ import generator_stop

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any, Callable, Container, Sequence, TypeVar

    T = TypeVar("T")


def extract_indexes(d):
    # type: (dict, ) -> Callable[[Sequence], dict]

    return lambda seq: {name: seq[index] for index, name in d.items()}


def bit_or(x, y):
    # type: (Any, Any) -> Any

    return x | y


def not_in(s):
    # type: (Container[T], ) -> Callable[[T], bool]

    return lambda x: x not in s


def operator_in(s):
    # type: (Container[T], ) -> Callable[[T], bool]

    """Comparable to stdlib `operator.itemgetter` type functions.
    It returns a function which will return a boolean indicating if
    its argument if in `s`. `s` should be a set-like for better performance.
    """

    return lambda x: x in s


def logical_xor(a, b):
    # type: (Any, Any) -> bool
    # this is just the != operator for bools

    return not (a and b) and (a or b)


def logical_xnor(a, b):
    # type: (Any, Any) -> bool
    # this is just the == operator for bools

    return not (a or b) or (a and b)


def logical_implication(a, b):
    # type: (Any, Any) -> bool

    """if a is True, b must be True"""

    return (not a) or b


def logical_nonimplication(a, b):
    # type: (Any, Any) -> bool

    """if a is True, b must be False"""

    return a and (not b)


def converse_implication(a, b):
    # type: (Any, Any) -> bool

    """if a is False, b must be False"""

    return a or (not b)


def converse_nonimplication(a, b):
    # type: (Any, Any) -> bool

    """if a is False, b must be True"""

    return (not a) and b
