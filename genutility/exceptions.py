from __future__ import absolute_import, division, print_function, unicode_literals

from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from typing import Any, Dict, Sequence, Set, TypeVar
	T = TypeVar("T")
	U = TypeVar("U")

class ParseError(Exception):
	""" Raised when the content to be parsed is malformed.
		Not a value error because usually the error is in some external resource
		which we don't have any control over.
	"""

class DownloadFailed(Exception):
	""" Raised when a download from an external resource by HTTP or any other protocol did not
		complete successfully. Could be raised anywhere between the initial TCP connection to
		a final integrity check.
	"""

class AccessDenied(Exception):
	pass

class TemporaryError(Exception):
	""" Signals that an failed operation can be retried in the future
		with a possibly different outcome.
	"""

class IteratorExhausted(Exception):
	""" Tried to get data from an exhausted Iterator. """

class WouldBlockForever(Exception):
	""" Raised when a blocking operation would wait forever. """

# results, control flow

class ControlFlowException(Exception):
	""" Not really an error, rather used for control flow handling
		where other constructs like `return` or `break` are not convenient.
	"""

class Skip(ControlFlowException):
	pass

class NoResult(ControlFlowException):
	""" Raised when an operation which maybe returns a result yields no result. """

class Break(ControlFlowException):
	""" Control flow exception to break out of a recursive call. """

class NoActionNeeded(ControlFlowException):
	""" Raised when nothing needs to be done / nothing was modified. """

# external errors

class ExternalError(Exception):
	""" Raised when an error occurs due to an external resource which we don't have control over,
		or are not the only actor to control it.
	"""

# aka ConsistencyError
class InconsistentState(ExternalError):
	""" This is either raised when some external resource changed without our knowledge,
		or when our code violates some consistency assumptions.
	"""

class ExternalProcedureUnavailable(ExternalError):
	""" If some external resource cannot be reached by API or RPC or is otherwise not able to handle
		the request, this is raised. It is not raised for invalid requests to the resource which are
		correctly handled (or rather correctly not handled in thie case).
	"""

class DatabaseUnavailable(ExternalError):
	""" Raised when the connection to a database fails because the database cannot be reached or
		raises and error related to the database itself and not to the query.
	"""

# runtime, possible coding errors

class ClosedObjectUsed(RuntimeError):

	def __init__(self, obj):
		RuntimeError.__init__(self, "{} is already closed".format(obj.__class__.__name__))

# values, input errors

class EmptyIterable(ValueError):
	""" Raised when Iterable is passed which doesn't yield any values,
		and thus not resulted can be computed.
	"""

class MalformedFile(ValueError):
	""" Raised when a malformed File is passes as input.
		In contrast to `ParseError` this is usually a file we have control over.
	"""

def assert_choice(name, value, choices, optional=False):
	# type: (str, T, Set[T], bool) -> None

	if optional and value is None:
		return

	if value not in choices:
		raise ValueError("{} must be one of {}".format(name, ", ".join(choices)))

def assert_choice_map(name, value, choices):
	# type: (str, T, Dict[T, U]) -> U

	try:
		return choices[value]
	except KeyError:
		raise ValueError("{} must be one of {}".format(name, ", ".join(choices.keys())))

def assert_type(name, value, types):
	# type: (str, Any, Sequence[Any]) -> None

	if not isinstance(value, types):
		raise TypeError("{} must be one of these types: {}".format(name, ", ".join(types)))

def assert_true(name, value):
	if not value:
		raise ValueError("{} must be set".format(name))
