from __future__ import absolute_import, division, print_function, unicode_literals

try:
	from sys import hash_info

	def get_wordsize():
		return hash_info.width

except ImportError:
	import struct
	wordsize = struct.calcsize("P") * 8

	def get_wordsize():
		return wordsize

__all__ = ["get_wordsize"]
