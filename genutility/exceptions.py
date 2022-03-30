from __future__ import generator_stop

from typing import Any, Dict, Optional, Sequence, Set, Tuple, Type, TypeVar, Union

T = TypeVar("T")
U = TypeVar("U")


class NotFound(LookupError):
    """Raised when a search doesn't turn up any results.
    Similar to KeyError or IndexError.
    """


class ParseError(Exception):
    """Raised when the content to be parsed is malformed.
    Not a value error because usually the error is in some external resource
    which we don't have any control over.
    """

    def __init__(self, *args, data=None):
        super().__init__(*args)
        self.data = data


class DownloadFailed(Exception):
    """Raised when a download from an external resource by HTTP or any other protocol did not
    complete successfully. Could be raised anywhere between the initial TCP connection to
    a final integrity check.
    """


class AccessDenied(Exception):
    cached: Optional[bool]


class TemporaryError(Exception):
    """Signals that an failed operation can be retried in the future
    with a possibly different outcome.
    """


class IteratorExhausted(Exception):
    """Tried to get data from an exhausted Iterator."""


class WouldBlockForever(Exception):
    """Raised when a blocking operation would wait forever."""


# results, control flow


class ControlFlowException(Exception):
    """Not really an error, rather used for control flow handling
    where other constructs like `return` or `break` are not convenient.
    """


class Skip(ControlFlowException):
    pass


class NoResult(ControlFlowException):
    """Raised when an operation which maybe returns a result yields no result."""


class Break(ControlFlowException):
    """Control flow exception to break out of a recursive call."""


class NoActionNeeded(ControlFlowException):
    """Raised when nothing needs to be done / nothing was modified."""


# external errors


class ExternalError(Exception):
    """Raised when an error occurs due to an external resource which we don't have control over,
    or are not the only actor to control it.
    """


# aka ConsistencyError
class InconsistentState(ExternalError):
    """This is either raised when some external resource changed without our knowledge,
    or when our code violates some consistency assumptions.
    """


class ExternalProcedureUnavailable(ExternalError):
    """If some external resource cannot be reached by API or RPC or is otherwise not able to handle
    the request, this is raised. It is not raised for invalid requests to the resource which are
    correctly handled (or rather correctly not handled in thie case).
    """


class DatabaseUnavailable(ExternalError):
    """Raised when the connection to a database fails because the database cannot be reached or
    raises and error related to the database itself and not to the query.
    """


# runtime, possible coding errors


class ClosedObjectUsed(RuntimeError):
    def __init__(self, obj):
        RuntimeError.__init__(self, f"{obj.__class__.__name__} is already closed")


# values, input errors


class EmptyIterable(ValueError):
    """Raised when Iterable is passed which doesn't yield any values,
    and thus not resulted can be computed.
    """


class MalformedFile(ValueError):
    """Raised when a malformed File is passes as input.
    In contrast to `ParseError` this is usually a file we have control over.
    """


def assert_choice(name: str, value: Optional[T], choices: Set[T], optional: bool = False) -> None:

    if optional and value is None:
        return

    if value not in choices:
        raise ValueError("{} must be one of {}".format(name, ", ".join(map(str, choices))))


def assert_choices(name, values, choices, optional=False):
    # type: (str, Optional[Sequence[T]], Set[T], bool) -> None

    if values is None:
        if optional:
            return
        else:
            raise TypeError("`None cannot be passed for `values` when `optional=False`")

    if set(values) - choices:
        raise ValueError("{} must be a subset of {}".format(name, ", ".join(map(str, choices))))


def assert_choice_map(name, value, choices):
    # type: (str, T, Dict[T, U]) -> U

    try:
        return choices[value]
    except KeyError:
        raise ValueError("{} must be one of {}".format(name, ", ".join(map(str, choices.keys()))))


def assert_type(name: str, value: Any, types: Union[Type[Any], Tuple[Type[Any], ...]]) -> None:

    if not isinstance(value, types):
        if not isinstance(types, tuple):
            types = (types,)
        raise TypeError(
            "{} must be one of these types: {}. Not: {}".format(name, ", ".join(map(str, types)), type(value))
        )


def assert_true(name, value):
    if not value:
        raise ValueError(f"{name} must be set")
