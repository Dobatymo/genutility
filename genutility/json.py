from __future__ import absolute_import, division, print_function, unicode_literals

import json

class BuiltinEncoder(json.JSONEncoder):
	def default(self, obj):
		if isinstance(obj, (set, frozenset)):
			return tuple(obj)
		elif isinstance(obj, complex):
			return [obj.real, obj.imag]

		return json.JSONEncoder.default(self, obj)
