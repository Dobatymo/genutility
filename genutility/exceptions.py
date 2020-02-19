from __future__ import absolute_import, division, print_function, unicode_literals

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
