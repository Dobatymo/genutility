from __future__ import absolute_import, division, print_function, unicode_literals

import struct, zlib

png_sig =  b"\x89PNG\r\n\x1a\n"

def png_chunk(type, data=""):
	# http://www.w3.org/TR/PNG/#5Chunk-layout
	length = struct.pack("!I", len(data))
	crc = zlib.crc32(type)
	crc = zlib.crc32(data, crc)
	crc = struct.pack("!i", crc)
	return length + type + data + crc

def IHDR(width, height):
	bitdepth = 1
	colortype = 0 #grayscale
	compression = 0
	filter = 0
	interlace = 0
	data = struct.pack("!IIBBBBB", width, height, bitdepth, colortype, compression, filter, interlace)

	return png_chunk("IHDR", data)

def IEND():
	return png_chunk("IEND", "")

def IDAT(binary, level=9):
	#ignores filter for scanlines
	return png_chunk("IDAT", zlib.compress(binary, level))

def binary2png(binary, width, height):
	return png_sig+IHDR(width, height)+IDAT(binary)+IEND()

__all__ = ["binary2png"]
