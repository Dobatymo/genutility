from __future__ import absolute_import, division, print_function, unicode_literals

import re

from .url import valid_uri_characters
from .string import replace_multiple

def extract_urls(text):
	pattern = r"https?\:\/\/[" + re.escape(valid_uri_characters) + r"]+"
	for match in re.finditer(pattern, text):
		url = match.group(0)
		yield url

def replace_typographical_punctuation(s):
	# type: (str, ) -> str

	""" Replaces typographical punctuation with ASCII punctuation. """

	d = {
		"‚": "'",
		"„": '"',
		"‘": "'",
		"’": "'",
		"“": '"',
		"”": '"',
		"‒": "-", # figure dash
		"–": "-", # en dash
		"—": "--", # em dash
		"―": "--", # horizontal bar
		"‗": "_", # double low line
		"…": "...", # horizontal ellipsis
	}
	return replace_multiple(s, d)
