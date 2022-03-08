from __future__ import generator_stop

from functools import reduce
from operator import mul
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Iterable, TypeVar

    from ..typing import Computable

    T = TypeVar("T")


try:
    from math import prod  # New in version 3.8

except ImportError:

    def prod(it, start=1):  # type: ignore
        # type: (Iterable[T], T) -> T

        """Counterpart to built-in `sum()`."""

        return reduce(mul, it, start)

    def prod_2(it, start=1):
        # type: (Iterable[Computable], Computable) -> Computable

        """Counterpart to built-in `sum()`."""

        for x in it:
            start *= x
        return start


try:
    from math import dist  # New in version 3.8
except ImportError:

    from math import sqrt

    def dist(p, q):
        return sqrt(sum((px - qx) ** 2.0 for px, qx in zip(p, q)))


try:
    from math import isqrt  # New in version 3.8

except ImportError:

    try:
        import gmpy2

        def isqrt(n):
            """Integer square root of `n`."""

            return int(gmpy2.isqrt(gmpy2.mpz(n)))

    except ImportError:

        def isqrt(n):
            """Integer square root of `n`.
            It uses float conversion and is not accurate for large numbers.
            Install `gmpy2` for improved speed and accuracy.
            """

            return int(n**0.5)
