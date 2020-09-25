from __future__ import absolute_import, division, print_function, unicode_literals

from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from typing import Optional

try:
	from secrets import token_urlsafe  # pylint: disable=unused-import

except ImportError: # python 3.5 and lower

	import base64
	import os

	DEFAULT_ENTROPY = 32

	def token_urlsafe(nbytes=None):
		# type: (Optional[int], ) -> str

		""" Return a random URL-safe text string, containing `nbytes` random bytes.
			The text is Base64 encoded, so on average each byte results in approximately 1.3 characters.
			If `nbytes` is None or not supplied, a reasonable default is used.
			>>> token_urlsafe(16)  
			'99B8rh_My-u5zCJSMhking'
		"""

		if nbytes is None:
			nbytes = DEFAULT_ENTROPY
		return base64.urlsafe_b64encode(os.urandom(nbytes)).rstrip(b"=").decode("ascii")
