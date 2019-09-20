from __future__ import absolute_import, division, print_function, unicode_literals

import logging
from io import open

from ..exceptions import MalformedFile

REAL_FILM_FPS = 24.
NTSC_PROG_FPS = 24000./1001
NTSC_VIDEO_FPS = 30000./1001
PAL_PROG_FPS = 25.
PAL_VIDEO_FPS = 30.

def ntsc_to_pal(num):
	return num * NTSC_PROG_FPS/PAL_PROG_FPS

def pal_to_ntsc(num):
	return num * PAL_PROG_FPS/NTSC_PROG_FPS

def film_to_ntsc(num):
	return num * REAL_FILM_FPS/NTSC_PROG_FPS

def to_msec(string):
	h, m, s, ms = [int(i) for i in string.replace(",", ":").replace(".", ":").split(":")]
	return (h * 60 * 60 + m * 60 + s)*1000 + ms

def to_srt_time(t):
	r, ms = divmod(t, 1000)
	r, s = divmod(r, 60)
	h, m = divmod(r, 60)
	return "{:02d}:{:02d}:{:02d},{:03d}".format(int(h), int(m), int(s), int(ms))

class Subtitle(object):

	def __init__(self):
		self.num = 0
		self.start = 0
		self.end = 0
		self.lines = []

	def get_times(self):
		return to_srt_time(self.start), to_srt_time(self.end)

	def set_times(self, start, end):
		self.start, self.end = to_msec(start), to_msec(end)

	def append(self, line):
		self.lines.append(line)

class SRTFile(object):

	nl = "\n"
	sep = " --> "

	def __init__(self, filename, mode="r", encoding="utf-8-sig", overwrite_index=False):
		self.state = 0
		self.linenum = 0
		self.sub_num = 0
		self.fp = open(filename, mode, encoding=encoding, errors="replace")
		self.overwrite_index = overwrite_index

	def __enter__(self):
		return self

	def __exit__(self, type, value, traceback):
		self.close()

	def close(self):
		self.fp.close()

	def write_subtitle(self, subtitle):

		start, end = subtitle.get_times()
		if self.overwrite_index:
			self.fp.write(str(self.sub_num) + self.nl)
		else:
			self.fp.write(str(subtitle.num) + self.nl)
		self.fp.write(start + self.sep + end + self.nl)
		for line in subtitle.lines:
			self.fp.write(line)
			self.fp.write(self.nl)
		self.fp.write(self.nl)
		self.sub_num += 1

	def read_line(self):
		self.linenum += 1
		line = next(self.fp).rstrip()

		if self.state == 0:
			try:
				self.sub.num = int(line)
			except ValueError:
				raise MalformedFile("Error in line {}: srt malformed: {}".format(self.linenum,line))
			self.state = 1
		elif self.state == 1:
			start, end = line.split(self.sep)
			self.sub.set_times(start, end)
			self.state = 2
		elif self.state == 2:
			if line == "":
				self.state = 0
			else:
				self.sub.append(line)

	def read_subtitle(self):
		self.sub = Subtitle()
		self.read_line()
		while self.state != 0:
			self.read_line() # can throw, and leave incomplete subtitle in buffer (eg. if file doesnt end in newline)
		return self.sub

	def __iter__(self):
		if self.fp:
			return self
		else:
			raise ValueError("I/O operation on closed file.")

	def __next__(self):
		return self.read_subtitle()

def transform(infile, outfile, callback, encoding):
	with SRTFile(infile, "r", encoding) as fi, SRTFile(outfile, "w", encoding) as fo:
		for subtitle in fi:
			subtitle = callback(subtitle)
			fo.write_subtitle(subtitle)

def merge(srtlines, lim):
	ret = []
	for l in srtlines:
		if l.startswith(lim):
			ret.append(l[len(lim):])
		else:
			if not ret:
				ret.append(l)
			else:
				ret[-1] = ret[-1] + " " + l
	return ret

def srt2txt(srt_fp):

	lim = "- "
	pos = 0
	lines = []

	while True:
		if pos >= len(lines):
			sub = next(srt_fp)
			lines = merge(sub.lines, lim)
			pos = 0
		ret = lines[pos]
		pos += 1
		yield ret

def compare_srt_and_txt(srt_file, txt_file):

	with SRTFile(srt_file, "r", encoding="utf-8-sig") as srt, open(txt_file, "r", encoding="utf-8-sig") as txt:

		srtiter = srt2txt(srt)

		limit = 10

		while limit > 0:
			try:
				l = next(txt).rstrip()
				if not l:
					continue
				if not l.startswith("- "):
					print(l)
				else:
					l = l[2:]
					start = 0
					while start <= len(l):
						srtpart = next(srtiter)
						txtpart = l[start:start+len(srtpart)]
						logging.debug("Compare '{}' '{}'".format(txtpart, srtpart))
						if txtpart != srtpart:
							#print("{} - {}".format(sub.start, sub.end))
							yield (txtpart, srtpart)
							limit -= 1
						start += len(srtpart) + 1
			except StopIteration:
				break
