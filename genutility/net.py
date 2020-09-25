from __future__ import absolute_import, division, print_function, unicode_literals

import re
import socket
from typing import TYPE_CHECKING

import netifaces

if TYPE_CHECKING:
	from typing import Optional

def is_ipv4(s):
	# type: (str, ) -> bool

	""" Tests if `s` is a IPv4 address string.
		It only validates the common `x.x.x.x` format and rejects less common ones like `x.x`.
	"""

	try:
		nums = tuple(map(int, s.split(".")))
		return len(nums) == 4 and min(nums) >= 0 and max(nums) <= 255
	except (AttributeError, ValueError):
		return False

simple_email_regex = r"[^@\s]+@[^@\s]+\.[^@\s]+"

def is_email(s):
	# type: (str, ) -> bool

	""" Coarse check to test of a string is an email. Will accept some invalid ones like
		"asd@.asd.com" and reject some valid ones like "asd@localhost"
	"""

	return re.fullmatch(simple_email_regex, s)

def get_standard_gateway(default=None):
	# type: (Optional[str], ) -> Optional[str]

	""" Returns the standard IPv4 gateway.
	"""

	for ipv4_gateway in netifaces.gateways()["default"][netifaces.AF_INET]:
		try:
			socket.inet_aton(ipv4_gateway)
			return ipv4_gateway
		except socket.error:
			pass

	return default
