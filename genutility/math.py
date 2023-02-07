from collections import Counter, defaultdict
from functools import partial
from itertools import islice
from math import factorial, log, pi, sqrt
from operator import gt, lt, mul
from random import sample
from typing import (
    Callable,
    DefaultDict,
    Hashable,
    Iterable,
    Iterator,
    List,
    Optional,
    Sequence,
    SupportsFloat,
    Tuple,
    TypeVar,
)

from .compat.math import isqrt, prod
from .exceptions import EmptyIterable
from .iter import range_count
from .typing import Computable, Orderable

OrderableT = TypeVar("OrderableT", bound=Orderable)

H = TypeVar("H", bound=Hashable)

inf = float("inf")


def reciprocal(n: Computable) -> Computable:
    return 1.0 / n


def sqr(x: Computable) -> Computable:
    """Returns `x` to the power of 2."""

    return x * x


def dot(a: Iterable[Computable], b: Iterable[Computable]) -> Computable:
    """Returns the dot product (inner product) of vectors `a` and `b`."""

    return sum(map(mul, a, b))


# was: euclidic_norm
def euclidean_norm(x: Iterable[Computable]) -> Computable:
    """Returns the Euclidean norm of vector `x`."""

    return sqrt(sum(map(sqr, x)))


def shannon_entropy(ps: Iterable[float], base: int = 2) -> float:
    """Calculates the Shannon entropy for probabilities `ps` with `base` in pure Python."""

    return -sum(p * log(p, base) for p in ps)


def cosine_similarity(a: Iterable[Computable], b: Iterable[Computable]) -> Computable:
    """Calculate the cosine similarity (normalized dot product) of vectors `a` and `b`."""

    return dot(a, b) / euclidean_norm(a) / euclidean_norm(b)


def argmin(seq: Sequence[OrderableT], s: int = 0, e: Optional[int] = None) -> OrderableT:
    if not seq:
        raise EmptyIterable()

    arg = s
    e = e or len(seq)
    for i in range(s + 1, e):
        if seq[i] < seq[arg]:
            arg = i
    return arg


def argmax(seq: Sequence[OrderableT], s: int = 0, e: Optional[int] = None) -> int:
    if not seq:
        raise EmptyIterable()

    arg = s
    e = e or len(seq)
    for i in range(s + 1, e):
        if seq[i] > seq[arg]:
            arg = i
    return arg


def argmax_pair(iterable: Iterable[OrderableT]) -> Tuple[int, OrderableT]:
    it = iter(iterable)
    arg = 0
    try:
        max = next(it)
    except StopIteration:
        raise EmptyIterable("empty iterable") from None

    for i, elm in enumerate(it, 1):
        if elm > max:
            arg = i
            max = elm

    return arg, max


from itertools import count
from operator import itemgetter


def argmax_v2(iterable: Iterable[OrderableT]) -> int:
    """nicer, but almost 2 times slower than above"""
    return max(zip(count(), iterable), key=itemgetter(1))[0]


def minmax(a: OrderableT, b: OrderableT) -> Tuple[OrderableT, OrderableT]:
    """`default` argument cannot be used, because the C level function doesn't have a default value
    but an overload.
    """

    if a <= b:
        return a, b
    else:
        return b, a


def _argfind_cmp(
    it: Iterable[OrderableT],
    target: OrderableT,
    op1: Callable[[OrderableT, OrderableT], bool],
    op2: Callable[[OrderableT, OrderableT], bool],
    pos: int = 0,
) -> Tuple[int, Optional[OrderableT]]:
    """Find the largest element in `it` less than or equal to `target` and return the index and value.
    Return (-1, None) if no such element can be found.
    """

    idx = -1
    val: Optional[OrderableT] = None

    it = islice(it, pos, None)
    try:
        v = next(it)
    except StopIteration:
        return idx, val

    if v == target:
        return pos, v
    elif op1(v, target):
        idx = pos
        val = v

    for i, v in enumerate(it, pos + 1):
        if v == target:
            return i, v
        elif op1(v, target) and (val is None or op2(v, val)):
            idx = i
            val = v

    return idx, val


def argfind_lte(it, target, pos=0):
    return _argfind_cmp(it, target, lt, gt, pos)


def argfind_gte(it, target, pos=0):
    return _argfind_cmp(it, target, gt, lt, pos)


def degree_to_rad(angle: float) -> float:
    return 2.0 * pi * angle / 360.0


def limit(x, left=0, right=1):
    if x >= left:
        if x <= right:
            return x
        else:
            return right
    else:
        return left


def relative_luminance(r: float, g: float, b: float) -> float:
    """Converts linear RGB components to relative luminance.
    See: https://en.wikipedia.org/wiki/Relative_luminance
    """

    return 0.2126 * r + 0.7152 * g + 0.0722 * b


class _PosInfInt:

    """A fancy version of `sys.maxsize`"""

    def __lt__(self, rhs) -> bool:
        return False

    def __gt__(self, rhs) -> bool:
        return True

    def __eq__(self, rhs) -> bool:
        if isinstance(rhs, _PosInfInt):
            raise ArithmeticError("Cannot compare inf with inf")

        return False

    def __add__(self, rhs) -> "_PosInfInt":
        return self

    def __sub__(self, rhs) -> "_PosInfInt":
        if isinstance(rhs, _PosInfInt):
            raise ArithmeticError("Cannot subtract inf from inf")

        return self

    def __str__(self) -> str:
        return "PosInfInt"

    def __repr__(self) -> str:
        return "PosInfInt"


PosInfInt = _PosInfInt()


def multinomial_coefficient(n: int, ks: Iterable[int]) -> int:
    return factorial(n) / prod(map(factorial, ks))


def num_unique_permutations(word: str) -> int:
    """Number of unique permutations of `word`."""

    return multinomial_coefficient(len(word), Counter(word).values())


def discrete_distribution(it: Iterable[H]) -> Tuple[DefaultDict[H, int], int]:
    """Creates a discrete distribution of the elements of `it`."""

    d: DefaultDict[H, int] = defaultdict(int)
    s = 0
    for i in it:
        s += 1
        d[i] += 1
    return d, s


def fibonaccigen(f0: int = 0, f1: int = 1) -> Iterator[int]:
    """A000045 [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, ...]
    arguments are the first two element of the Fibonacci series

    To get a specific Fibonacci number use `fibonacci(n)`.
    """

    yield f0
    while True:
        yield f1
        f1, f0 = f1 + f0, f1


def floordiv2(n: int) -> Iterator[int]:
    while n > 0:
        yield n
        n = n // 2


def isintlog(num: int, base: int) -> bool:
    if num <= 0 or base <= 0:
        raise ValueError("num and base must be larger than 0")

    if num == 1:
        return False

    while num > 1:
        r = num % base
        if r != 0:
            return False
        num //= base

    return True


def _fibonacci(n: int) -> Tuple[int, int]:
    # returns (F(n), F(n+1)).
    # inspired by https://www.nayuki.io/page/fast-fibonacci-algorithms

    a, b = 0, 1
    for i in reversed(tuple(floordiv2(n))):
        c = a * (b * 2 - a)
        d = a * a + b * b
        if i % 2 == 0:
            a = c
            b = d
        else:
            a = d
            b = c + d
    return a, b


# from .numba import opjit
# @opjit() # doesn't support arbitrary large ints
def _fibonacci_v2(n: int) -> Tuple[int, int]:
    # see: https://stackoverflow.com/a/1526036
    # 'Structure and Interpretation of Computer Programs' (SICP) ex 1.19
    # http://community.schemewiki.org/?sicp-ex-1.19

    a, b, p, q = 1, 0, 0, 1
    while n > 0:
        if n % 2 == 0:  # even
            oldp = p
            p = p * p + q * q
            q = 2 * oldp * q + q * q
            n //= 2
        else:
            olda = a
            a = b * q + a * q + a * p
            b = b * p + olda * q
            n -= 1
    return a, b


def fibonacci(n: int) -> int:
    """implementation of "fast doubling". can be derived from this identity:
    [[1, 1], [1, 0]]^n = [[F_n+1, F_n], [F_n, F_n-1]]
    """

    if n == 0:
        return 0
    elif n < 0:
        raise ValueError("Negative arguments not implemented")

    return _fibonacci(n - 1)[1]


def byte2size(byte: SupportsFloat, exp: int = 0, base: int = 1024) -> Tuple[float, str]:
    """Converts integer number to float and unit string"""

    byte = float(byte)
    byte_units = ("Byte", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB")

    for unit in islice(byte_units, exp, None):
        if byte >= base:
            byte /= base
        else:
            break

    return byte, unit


def byte2size_str(byte: SupportsFloat, roundval: int = 3) -> str:
    """Converts integer number to human readable size string."""

    byte, value = byte2size(byte)
    if value == "Byte":
        roundval = 0
    return "{:.{}f} {}".format(byte, roundval, value)


def primes(stop: Optional[int] = None) -> Iterable[int]:
    """Naive algorithm to yield all primes which are smaller than `stop`.
    If `stop` is None it will never stop generating primes.
    For better algorithms see here: https://stackoverflow.com/questions/2211990/how-to-implement-an-efficient-infinite-generator-of-prime-numbers-in-python/10733621#10733621
    """

    found_primes: List[int] = []
    first_prime = 2

    for i in range_count(first_prime, stop):
        is_prime = True
        for j in found_primes:
            if j > isqrt(i):
                break
            if i % j == 0:
                is_prime = False
                break

        if is_prime:
            found_primes.append(i)
            yield i


def additaet(n: int) -> int:
    """sums all numbers from 0 to n using Gaussian formula.
    basically same performance
            (n*n + n) >> 1
    too slow, floats
            int(((n/2.0) + 0.5) * n)
            int((n + 1) / 2.0 * n)
    too slow, worse complexity
            sum(range(n+1))
    """

    return ((n + 1) * n) >> 1


addity = additaet


def digitsum(n: int) -> int:
    """Use for numbers with more than 6 digits."""

    return sum(map(int, str(n)))


def digitsum_small(n: int) -> int:
    """Use for numbers with less than 6 digits."""

    s = 0
    while n:
        s += n % 10
        n //= 10
    return s


def digitsum_base(n: int, base: int = 10) -> int:
    """Use with string input if base is not 10."""

    return sum(map(partial(int, base=base), str(n)))


def euclidean_distance(a: Computable, b: Computable) -> Computable:
    """Euclidean distance between `a` and `b`."""

    return abs(b - a)


def closest(
    numbers: Iterable[Computable],
    number: Computable,
    distance_func: Callable[[Computable, Computable], Computable] = euclidean_distance,
) -> Computable:
    """For a list of `numbers`, return the closest number to `number`."""

    return min(numbers, key=partial(distance_func, number))


def absolute_difference(a: Computable, b: Computable) -> Computable:
    return abs(b - a)


def sortedsample(n: int, k: int) -> List[int]:
    """Sorted random sample without replacements."""

    return sorted(sample(range(n), k))


number_metric = absolute_difference

if __name__ == "__main__":
    import timeit

    print(min(timeit.repeat(stmt="digitsum(111111)", setup="from __main__ import digitsum")))
    print(min(timeit.repeat(stmt="digitsum_base(111111)", setup="from __main__ import digitsum_base")))
    # print(min(timeit.repeat('_fibonacci_v2(999999999999999999999999999999999)', setup="from __main__ import _fibonacci_v2")))
