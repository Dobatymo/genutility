from collections import defaultdict
from contextlib import nullcontext
from difflib import unified_diff
from functools import wraps
from itertools import product, zip_longest
from os import remove
from tempfile import NamedTemporaryFile
from time import sleep
from typing import IO, Any, Callable, Collection, DefaultDict, Hashable, Iterable, Mapping, Optional, Tuple, TypeVar
from unittest import TestCase
from unittest.result import TestResult
from unittest.runner import TextTestRunner

from .file import _check_arguments, equal_files
from .signal import HandleKeyboardInterrupt  # problem here

T = TypeVar("T")
U = TypeVar("U")


anullcontext = nullcontext()


def print_file_diff(fromfile: str, tofile: str, encoding: str) -> None:
    with open(fromfile, encoding=encoding) as fr:
        fromlines = fr.readlines()
    with open(tofile, encoding=encoding) as fr:
        tolines = fr.readlines()

    for line in unified_diff(fromlines, tolines, fromfile, tofile):
        print(line, end="")


class MyTestResult(TestResult):
    """Extension of TestResult to support numbering test cases"""

    def __init__(self, stream: IO[str], descriptions, verbosity):
        """Initializes the test number generator, then calls super impl"""
        self.stream = stream
        self.current_test = 0
        self.current_subtest = 0
        return TestResult.__init__(self, stream, descriptions, verbosity)

    def progress(self) -> None:
        self.stream.write(f"Running test #{self.current_test}, subtest #{self.current_subtest}\r")

    def startTest(self, test) -> None:
        self.current_test += 1
        TestResult.startTest(self, test)
        self.progress()

    def stopTest(self, test) -> None:
        TestResult.stopTest(self, test)

    def stopTestRun(self) -> None:
        self.stream.write("\n")
        TestResult.stopTestRun(self)

    def addSubTest(self, test, subtest, outcome) -> None:
        """Called when a subtest finishes."""

        TestResult.addSubTest(self, test, subtest, outcome)
        self.testsRun += 1
        self.current_subtest += 1
        self.progress()


class MyTestRunner(TextTestRunner):
    """Extension of TestRunner to support numbering test cases"""

    resultclass = MyTestResult

    def run(self, test):
        """Stores the total count of test cases, then calls super impl"""

        self.total_test_cases = test.countTestCases()
        return TextTestRunner.run(self, test)

    def _makeResult(self):
        return TextTestRunner._makeResult(self)


class NoRaise:
    def __init__(self, testcase: TestCase, message: Optional[str] = None) -> None:
        self.testcase = testcase
        self.message = message

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type:
            if self.message:
                self.testcase.fail(self.message)
            else:
                self.testcase.fail(exc_value)


def make_comparable(d: Any) -> Any:
    if isinstance(d, (str, int, type(None))):
        return d
    elif isinstance(d, list):
        return list(make_comparable(i) for i in d)
    elif isinstance(d, tuple):
        return tuple(make_comparable(i) for i in d)
    elif isinstance(d, dict):
        return make_comparable(list(d.items()))
    else:
        raise ValueError(f"must be list, tuple or dict, not {type(d)}")


def is_equal_unordered(seq_a: Collection, seq_b: Collection) -> bool:
    if isinstance(seq_a, set) and isinstance(seq_b, set):
        return seq_a == seq_b

    seq_a = sorted(make_comparable(seq_a))
    seq_b = sorted(make_comparable(seq_b))
    return seq_a == seq_b


class MyTestCase(TestCase):
    def subTest(self, msg=None, **params):
        try:
            func = TestCase.subTest
        except AttributeError:
            return anullcontext
        else:
            return func(self, msg, **params)

    def assertAnd(self, first: Any, second: Any, msg: Optional[str] = None) -> None:
        self.assertTrue(first and second, msg)

    def assertTypeEqual(self, first: Any, second: Any, msg: Optional[str] = None) -> None:
        self.assertEqual(type(first), type(second), msg)

    def assertFilesEqual(self, first_path: Any, second_path: Any, msg: Optional[str] = None) -> None:
        self.assertTrue(equal_files(first_path, second_path), msg)

    def assertIterEqual(self, first: Iterable, second: Iterable, msg: Optional[str] = None) -> None:
        for i, (a, b) in enumerate(zip_longest(first, second)):
            if msg:
                msg = " : " + str(msg)
            self.assertEqual(a, b, msg=f"in iteration index {i}: {msg}")

    def assertIterAlmostEqual(self, first: Iterable, second: Iterable, msg: Optional[str] = None) -> None:
        for i, (a, b) in enumerate(zip_longest(first, second)):
            if msg:
                msg = " : " + str(msg)
            try:
                self.assertAlmostEqual(a, b, msg=f"in iteration index {i}: {msg}")
            except TypeError:
                raise AssertionError("Invalid types (probably different length iters)")  # from None

    def assertAllEqual(self, args: Iterable, msg: Optional[str] = None) -> None:  # *args doesn't work in python2!?
        it = iter(args)
        first = next(it)
        for second in it:
            self.assertEqual(first, second, msg)

    def assertIterIterEqual(
        self, first: Iterable[Iterable], second: Iterable[Iterable], msg: Optional[str] = None
    ) -> None:  # UNTESTED
        for i, (a, b) in enumerate(zip_longest(first, second)):
            if msg:
                msg = " : " + str(msg)
            self.assertIterEqual(a, b, msg=f"in iteration index {i}: {msg}")

    def assertPriorityEqual(
        self,
        first: Iterable[Optional[Tuple[Hashable, Hashable]]],
        second: Iterable[Optional[Tuple[Hashable, Hashable]]],
        msg: Optional[str] = None,
    ) -> None:
        d1: DefaultDict[Hashable, set] = defaultdict(set)
        d2: DefaultDict[Hashable, set] = defaultdict(set)

        for a, b in zip_longest(first, second):
            if a is not None:
                val_1, p_1 = a
                if b is None and p_1 == 0:
                    continue

            if b is not None:
                val_2, p_2 = b
                if a is None and p_2 == 0:
                    continue

            self.assertAnd(a, b)

            if val_1 == 0 and val_2 == 0:
                continue

            d1[p_1].add(val_1)
            d2[p_2].add(val_2)
        self.assertEqual(d1, d2, msg)

    def assertUnorderedSeqEqual(self, first: Iterable, second: Iterable, msg: Optional[str] = None) -> None:
        # fixme: use is_equal_unordered

        first = sorted(first)
        second = sorted(second)
        self.assertEqual(first, second, msg)

    def assertNoRaise(self, msg: Optional[str] = None) -> NoRaise:
        return NoRaise(self, msg)

    def assertEqualsOneOf(self, result: T, truths: Iterable[T]) -> None:
        for truth in truths:
            if result == truth:
                return

        raise AssertionError("Result does not match one of the provided truths")  # from None

    def assertUnorderedMappingEqual(
        self, first: Mapping[T, U], second: Mapping[T, U], msg: Optional[str] = None
    ) -> None:
        self.assertEqual(len(first), len(second), msg)

        for a, b in zip(sorted(first.keys()), sorted(second.keys())):
            self.assertEqual(a, b)
            self.assertEqual(first[a], second[b])


def random_arguments(n: int, *funcs: Callable[[], Any]) -> Callable[[Callable], Callable]:
    def decorator(func):
        @wraps(func)
        def inner(self):
            for i in range(n):
                with self.subTest(str(i)):
                    if func(self, *(f() for f in funcs)) is not None:
                        raise AssertionError

        return inner

    return decorator


# also called: parameterize
def parametrize(*args_list: tuple) -> Callable[[Callable], Callable]:
    def decorator(func):
        @wraps(func)
        def inner(self):
            for args in args_list:
                with self.subTest(str(args)[:1000]):
                    if func(self, *args) is not None:
                        raise AssertionError

        return inner

    return decorator


def parametrize_product(*args_list: tuple) -> Callable[[Callable], Callable]:
    def decorator(func):
        @wraps(func)
        def inner(self):
            for args in product(*args_list):
                with self.subTest(str(args)):
                    if func(self, *args) is not None:
                        raise AssertionError

        return inner

    return decorator


def repeat(number: int) -> Callable[[Callable], Callable]:
    def decorator(func):
        @wraps(func)
        def inner(self):
            for i in range(number):
                if func(self) is not None:  # no self.subTest(str(i))
                    raise AssertionError

        return inner

    return decorator


class closeable_tempfile:
    Uninterrupted = HandleKeyboardInterrupt()

    def __init__(self, mode="w+b", encoding=None):
        encoding = _check_arguments(mode, encoding)
        self.f = NamedTemporaryFile(mode=mode, encoding=encoding, delete=False)

    def __enter__(self):
        return self.f, self.f.name

    def __exit__2(self, type, value, traceback):
        with self.Uninterrupted:
            self.f.close()  # close in case user has not closed the file
            remove(self.f.name)

    def __exit__(self, type, value, traceback):
        try:
            if type == EOFError:
                sleep(1)  # wait for KeyboardInterrupt which might follow EOFError...
        finally:
            self.f.close()  # close in case user has not closed the file
            remove(self.f.name)
