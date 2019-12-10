from __future__ import absolute_import, division, print_function, unicode_literals

import re

from .url import valid_uri_characters

def extract_urls(text):
	pattern = r"https?\:\/\/[" + re.escape(valid_uri_characters) + r"]+"
	for match in re.finditer(pattern, text):
		url = match.group(0)
		yield url
