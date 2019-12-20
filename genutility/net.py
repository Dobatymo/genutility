from __future__ import absolute_import, division, print_function, unicode_literals

import socket
import netifaces

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

def get_standard_gateway(default=None):
	# type: (Optional[str], ) -> Optional[str]

	for ipv4_gateway in netifaces.gateways()["default"][netifaces.AF_INET]:
		try:
			socket.inet_aton(ipv4_gateway)
			return ipv4_gateway
		except socket.error:
			pass

	return default
