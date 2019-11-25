from __future__ import absolute_import, division, print_function, unicode_literals

import sys, os, os.path, logging

from .filesystem import statsislink, isdir, extract_basic_stat_info

def path_split(path):
	head, tail = os.path.split(path)
	root, ext = os.path.splitext(tail)
	return (head, root, ext[1:])

def path_convert_sep(path):
	"""Converts \ to /"""
	return path.replace("\\", "/")

def path_norm(path):
	drive, path = os.path.splitdrive(path)
	return path_convert_sep(os.path.normpath(path))

def path_abs_rel(path, relpath, abs_rel=0):
	"""abs_rel
	0: standard behaviour, abs if directory=abs, rel if directory=rel
	1: abs path
	2: rel path
	3: filename only"""
	if abs_rel == 0:
		return path
	elif abs_rel == 1:
		return os.path.abspath(path)
	elif abs_rel == 2:
		return os.path.relpath(path, relpath)
	elif abs_rel == 3:
		return os.path.basename(path)
	else:
		raise ValueError("abs_rel must be between 0 and 3 inclusive")

#implement more abs,rel options
def listdir_rec(directory, dirs=True, files=True, rec=True, abs_rel=0, link=True, meta=False, onerror=None):
	"""abs_rel
	0: standard behaviour, abs if directory=abs, rel if directory=rel
	1: abs path
	2: rel path
	3: filename only"""

	if type(rec) == bool and rec == True:
		rec = -1

	try:
		for i in os.listdir(directory):
			next = os.path.join(directory, i)
			stats = os.lstat(next)
			if not isdir(stats):
				if statsislink(stats): # fix 2017-06-19, does not work for junctions...
					print("Skipping link")
					continue
				#((not A) and B) or (A and B and C) == (not A or C) and B
				if files and (not isdir(stats) or link):
					if meta:
						yield (path_abs_rel(next, directory, abs_rel), stats) #path_abs_rel needed?
					else:
						yield path_abs_rel(next, directory, abs_rel) #path_abs_rel needed?
			else:
				if statsislink(stats):
					raise RuntimeError("Directory links are not supported yet")

				if dirs:
					if meta:
						yield (path_abs_rel(next, directory, abs_rel), stats) #path_abs_rel needed?
					else:
						yield path_abs_rel(next, directory, abs_rel) #path_abs_rel needed?
				if rec:
					if meta:
						for sub, substats in listdir_rec(next, dirs, files, rec-1, abs_rel=0, meta=meta, onerror=onerror):
							yield (path_abs_rel(sub, directory, abs_rel), substats) #path_abs_rel needed?
					else:
						for sub in listdir_rec(next, dirs, files, rec-1, abs_rel=0, meta=meta, onerror=onerror):
							yield path_abs_rel(sub, directory, abs_rel)

	except OSError as e:
		if onerror:
			onerror(None, None, sys.exc_info())

def listdir_rec_meta(directory, dirs=True, files=True, rec=True, abs_rel=0):
	for path, stats in listdir_rec(directory, dirs, files, rec, abs_rel, meta=True):
		yield (path, extract_basic_stat_info(stats))

def listdir_rec_adv(directory, dirs=True, files=True, rec=True, total=False):
	try:
		dir_count = 0
		file_count = 0
		for i in os.listdir(directory):
			next = os.path.join(directory, i)
			if not os.path.isdir(next):
				file_count += 1
				if files:
					yield (next, 0, 0)
			else:
				dir_count += 1
				if rec:
					for j, dc, fc in listdir_rec_adv(next, dirs, files, rec, total):
						yield (j, dc, fc)
						if total:
							dir_count += dc
							file_count += fc
		if dirs:
			yield (directory, dir_count, file_count)

	except IOError: pass
	except WindowsError: pass

def folder_contents_rec(directory):
	contents = []
	n = 0
	try:
		for i in os.listdir(directory):
			next = os.path.join(directory, i)
			n += 1
			if os.path.isdir(next):
				contents.extend(folder_contents_rec(next))
		contents.append((directory, n))
	except Exception as e:
		logging.exception("Enumerating directory failed")
		contents.append(("dummy", -1))
	return contents
