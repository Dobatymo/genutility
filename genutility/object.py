from __future__ import absolute_import, division, print_function, unicode_literals

from copy import copy

def cast(object, class_, instanceof=object, *args, **kwargs):
	""" Changes the class of `object` to `class_` if `object` is an instance of `instanceof`,
		calls the initializer and returns it.
	"""

	object = copy(object)
	if isinstance(object, instanceof):
		object.__class__ = class_
		object.__init__(*args, **kwargs)
	else:
		raise TypeError("Object is not an instance of {}".format(instanceof.__name__))
	return object
