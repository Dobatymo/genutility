from __future__ import absolute_import, division, print_function, unicode_literals

try:
	from importlib.util import find_spec

except ImportError:
	def find_spec(name):
		# type: (str, ) -> dict

		""" Find the spec for a module. `name` must be importable. """

		from importlib import import_module 
		module = import_module(name)

		ret = {
			"name": module.__name__,
			"origin": module.__file__,
			"has_location": False,
			"submodule_search_locations": []
		}

		try:
			if module.__path__:
				ret.update({
					"has_location": True,
					"submodule_search_locations": [module.__path__],
				})
				return ret
		except AttributeError:
			pass

		return ret
