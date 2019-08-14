from __future__ import absolute_import, division, print_function, unicode_literals

import logging
from io import open

from ..exceptions import MalformedFile

class Subtitle:

	def __init__(self, start, end, lines):
		self.start = start
		self.end = end
		self.lines = lines

class Sub:
	""" MicroDVD subtitle """

	sep = "|"

	def __init__(self, filename, mode="r", encoding="utf-8-sig"):
		self.fp = open(infile, mode, encoding)

	def __enter__(self):
		return self

	def __exit__(self, exc_type, exc_value, traceback):
		self.close()

	def _readline(self):
		line = next(self.fi).rstrip()

		start, end, text = l.split("}", 2)
		try:
			start, end = int(start[1:]), int(end[1:])
		except:
			MalformedFile("Error in line {}: sub malformed: {}".format(i,l))

		return Subtitle(start, end, text.split(self.sep))

	def readline(self):
		try:
			return self._readline()
		except StopIteration:
			return None

	def __iter__(self):
		return self

	def __next__(self):
		return self._readline()

	def write_subtitles(self, subtitle):
		self.fp.write("{{{}}}{{{}}}{}\n".format(subtitle.start, subtitle.end, self.sep.join(subtitle)))

	def close(self):
		self.fp.close()
