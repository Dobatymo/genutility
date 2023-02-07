from math import pow
from random import sample
from typing import Collection

from .compat.math import prod
from .math import reciprocal


def sample_range(total, num):
    return sample(range(total), min(num, total))


def arithmetic_mean(col: Collection) -> float:
    """Arithmetic mean of `col`."""

    return sum(col) / len(col)


mean = arithmetic_mean


def harmonic_mean(col: Collection) -> float:
    """Harmonic mean of `col`."""

    return len(col) / sum(map(reciprocal, col))


def geometric_mean(col: Collection) -> float:
    """Geometric mean of `col`."""

    return pow(prod(col), reciprocal(len(col)))
