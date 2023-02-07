from typing import Any, Callable, Container, Sequence, TypeVar

T = TypeVar("T")


def extract_indexes(d: dict) -> Callable[[Sequence], dict]:
    return lambda seq: {name: seq[index] for index, name in d.items()}


def bit_or(x: Any, y: Any) -> Any:
    return x | y


def not_in(s: Container[T]) -> Callable[[T], bool]:
    return lambda x: x not in s


def operator_in(s: Container[T]) -> Callable[[T], bool]:
    """Comparable to stdlib `operator.itemgetter` type functions.
    It returns a function which will return a boolean indicating if
    its argument if in `s`. `s` should be a set-like for better performance.
    """

    return lambda x: x in s


def logical_xor(a: Any, b: Any) -> bool:
    # this is just the != operator for bools

    return not (a and b) and (a or b)


def logical_xnor(a: Any, b: Any) -> bool:
    # this is just the == operator for bools

    return not (a or b) or (a and b)


def logical_implication(a: Any, b: Any) -> bool:
    """if a is True, b must be True"""

    return (not a) or b


def logical_nonimplication(a: Any, b: Any) -> bool:
    """if a is True, b must be False"""

    return a and (not b)


def converse_implication(a: Any, b: Any) -> bool:
    """if a is False, b must be False"""

    return a or (not b)


def converse_nonimplication(a: Any, b: Any) -> bool:
    """if a is False, b must be True"""

    return (not a) and b
