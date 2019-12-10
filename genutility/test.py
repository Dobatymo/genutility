from __future__ import absolute_import, division, print_function, unicode_literals

from builtins import range, input
from future.moves.itertools import zip_longest
from future.utils import PY2

from unittest import TestCase
from unittest.runner import TextTestRunner
from unittest.result import TestResult
from os import remove
from collections import defaultdict
from functools import wraps
from itertools import product
from tempfile import NamedTemporaryFile
from time import sleep
from io import TextIOWrapper
from typing import TYPE_CHECKING

from .ops import logical_xor, logical_implication
from .file import equal_files, _check_arguments
from .signal import HandleKeyboardInterrupt # problem here

if TYPE_CHECKING:
	from typing import Any, Iterable, Optional, Hashable, Tuple, Callable, DefaultDict

class nullcontext(object): # see: .compat.contextlib

	def __init__(self, *args, **kwargs):
		pass

	def __enter__(self):
		return self

	def __exit__(self, exc_type, exc_value, traceback):
		pass

anullcontext = nullcontext()

class MyTestResult(TestResult):
	"""Extension of TestResult to support numbering test cases"""

	def __init__(self, stream, descriptions, verbosity):
		"""Initializes the test number generator, then calls super impl"""
		self.stream = stream
		self.current_test = 0
		self.current_subtest = 0
		return TestResult.__init__(self, stream, descriptions, verbosity)

	def progress(self):
		self.stream.write("Running test #{}, subtest #{}\r".format(self.current_test, self.current_subtest))

	def startTest(self, test):
		self.current_test += 1
		TestResult.startTest(self, test)
		self.progress()

	def stopTest(self, test):
		TestResult.stopTest(self, test)

	def stopTestRun(self):
		self.stream.write("\n")
		TestResult.stopTestRun(self)

	def addSubTest(self, test, subtest, outcome):
		""" Called when a subtest finishes. """

		TestResult.addSubTest(self, test, subtest, outcome)
		self.testsRun += 1
		self.current_subtest += 1
		self.progress()

class MyTestRunner(TextTestRunner):
	"""Extension of TestRunner to support numbering test cases"""

	resultclass = MyTestResult

	def run(self, test):
		"""Stores the total count of test cases, then calls super impl"""

		total_test_cases = test.countTestCases()
		return TextTestRunner.run(self, test)

	def _makeResult(self):
		return TextTestRunner._makeResult(self)

class NoRaise(object):

	def __init__(self, testcase, message=None):
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

class MyTestCase(TestCase):

	def subTest(self, msg=None, **params):
		try:
			func = TestCase.subTest
		except AttributeError:
			return anullcontext
		else:
			return func(self, msg, **params)

	def assertAnd(self, first, second, msg=None):
		# type: (Any, Any, Optional[str]) -> None

		self.assertTrue(first and second, msg)

	def assertFilesEqual(self, first_path, second_path):
		self.assertTrue(equal_files(first_path, second_path))

	def assertIterEqual(self, first, second, msg=None):
		# type: (Iterable, Iterable, Optional[str]) -> None

		for i, (a, b) in enumerate(zip_longest(first, second)):
			if msg:
				msg = " : " + str(msg)
			self.assertEqual(a, b, msg="in iteration index {}: {}".format(i, msg))

	def assertIterAlmostEqual(self, first, second, msg=None):
		# type: (Iterable, Iterable, Optional[str]) -> None

		for i, (a, b) in enumerate(zip_longest(first, second)):
			if msg:
				msg = " : " + str(msg)
			try:
				self.assertAlmostEqual(a, b, msg="in iteration index {}: {}".format(i, msg))
			except TypeError:
				# assert False, "Invalid types (probably different length iters)"
				raise AssertionError("Invalid types (probably different length iters)") # from None

	def assertAllEqual(self, args, msg=None): # *args doesn't work in python2!?
		# type: (Iterable, Optional[str]) -> None

		it = iter(args)
		first = next(it)
		for second in it:
			self.assertEqual(first, second, msg)

	def assertIterIterEqual(self, first, second, msg=None): # UNTESTED
		# type: (Iterable[Iterable], Iterable[Iterable], Optional[str]) -> None

		for i, (a, b) in enumerate(zip_longest(first, second)):
			if msg:
				msg = " : " + str(msg)
			self.assertIterEqual(a, b, msg="in iteration index {}: {}".format(i, msg))

	def assertPriorityEqual(self, first, second, msg=None):
		# type: (Iterable[Optional[Tuple[Hashable, Hashable]]], Iterable[Optional[Tuple[Hashable, Hashable]]], Optional[str]) -> None

		d1 = defaultdict(set) # type: DefaultDict[Hashable, set]
		d2 = defaultdict(set) # type: DefaultDict[Hashable, set]

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

	def assertUnorderedSeqEqual(self, first, second, msg=None):
		# type: (Iterable, Iterable, Optional[str]) -> None

		first = sorted(first)
		second = sorted(second)
		self.assertEqual(first, second, msg)

	def assertNoRaise(self, msg=None):
		return NoRaise(self, msg)

def random_arguments(n, *funcs):
	# type: (int, *Callable[[], Any]) -> Callable[[Callable], Callable]

	def decorator(func):
		@wraps(func)
		def inner(self):
			for i in range(n):
				with self.subTest(str(i)):
					assert func(self, *(f() for f in funcs)) is None
		return inner
	return decorator

# also called: parameterize
def parametrize(*args_list):
	# # type: (*tuple, ) -> Callable[[Callable], Callable] # mypy error: syntax error in type comment

	def decorator(func):
		@wraps(func)
		def inner(self):
			for args in args_list:
				with self.subTest(str(args)):
					assert func(self, *args) is None
		return inner
	return decorator

def parametrize_product(*args_list):
	# # type: (*tuple, ) -> Callable[[Callable], Callable] # mypy error: syntax error in type comment

	def decorator(func):
		@wraps(func)
		def inner(self):
			for args in product(*args_list):
				with self.subTest(str(args)):
					assert func(self, *args) is None
		return inner
	return decorator

def repeat(number):
	# type: (int, ) -> Callable[[Callable], Callable]

	def decorator(func):
		@wraps(func)
		def inner(self):
			for i in range(number):
				assert func(self) is None # no self.subTest(str(i))
		return inner
	return decorator

class closeable_tempfile(object):

	Uninterrupted = HandleKeyboardInterrupt()

	def __init__(self, mode="w+b", encoding=None):

		encoding = _check_arguments(mode, encoding)

		if PY2:
			ntf = NamedTemporaryFile(mode=mode, delete=False)
			if encoding:
				ntf.readable = lambda: True
				ntf.writable = lambda: True
				ntf.seekable = lambda: True

				self.f = TextIOWrapper(ntf, encoding)
			else:
				self.f = ntf
		else:
			self.f = NamedTemporaryFile(mode=mode, encoding=encoding, delete=False)

	def __enter__(self):
		return self.f, self.f.name

	def __exit__2(self, type, value, traceback):
		with self.Uninterrupted:
			self.f.close() # close in case user has not closed the file
			remove(self.f.name)

	def __exit__(self, type, value, traceback):
		try:
			if type == EOFError:
				sleep(1) # wait for KeyboardInterrupt which might follow EOFError...
		finally:
			self.f.close() # close in case user has not closed the file
			remove(self.f.name)
