from __future__ import absolute_import, division, print_function, unicode_literals

class ParseError(Exception):
	pass

class AccessDenied(Exception):
	pass

class TemporaryError(Exception):
	pass

class IteratorExhausted(Exception):
	pass

# results, control flow

class Skip(Exception):
	pass

class NoResult(Exception):
	pass

# external errors

class InconsistentState(Exception):
	pass

# values, input errors

class EmptyIterable(ValueError):
	pass

class MalformedFile(ValueError):
	pass
