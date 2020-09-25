from __future__ import absolute_import, division, print_function, unicode_literals

# from builtins import str # don't do this here because of cookie construction!
from future.utils import PY2, iteritems

from http.cookies import SimpleCookie as IncompatibleSimpleCookie

if PY2:
	class SimpleCookie(IncompatibleSimpleCookie):

		def __init__(self, rawdata):
			if isinstance(rawdata, dict):
				rawdata = {str(k): v for k, v in iteritems(rawdata)}
			elif isinstance(rawdata, unicode): # noqa: F821
				rawdata = str(rawdata)

			IncompatibleSimpleCookie.__init__(self, rawdata)
else:
	SimpleCookie = IncompatibleSimpleCookie
