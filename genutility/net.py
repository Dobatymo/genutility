from __future__ import absolute_import, division, print_function, unicode_literals

import socket
import netifaces

def get_standard_gateway(default=None):
	for ipv4_gateway in netifaces.gateways()["default"][netifaces.AF_INET]:
		try:
			socket.inet_aton(ipv4_gateway)
			return ipv4_gateway
		except socket.error:
			pass
	return default
