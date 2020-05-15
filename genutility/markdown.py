from __future__ import absolute_import, division, print_function, unicode_literals

import re

_markdown_newline_pat = re.compile(r"[^\n]\n[^\n]")
_markdown_newline_func = lambda x: x.group(0).replace("\n", "  \n")

def markdown_newline(s):
	# type: (str, ) -> str

	""" Convert newlines to markdown linebreaks. """

	return _markdown_newline_pat.sub(_markdown_newline_func, s)

_markdown_urls_pat = re.compile(r"(?<![\<])((?:http|https|ftp):\/\/[a-zA-Z0-9\-\.]+\.[a-zA-Z0-9]{2,}(?:\/[\:\/\?\#\[\]\@\!\$\&\'\(\)\*\+\;\=a-zA-Z0-9\-\._\~\%]*)?)(?![\>])")

def markdown_urls(s, ignore_trailing_dot=True):
	# type: (str, ) -> str

	""" Converts text with URLs to text with markdown formatted URLs.
		markdown_urls("Visit https://google.com") -> "Visit <https://google.com>"
		This function is idempotent, which means that it will not convert URLs which are already in the correct format.
		markdown_urls("Visit <https://google.com>") -> "Visit <https://google.com>"
	"""

	def markdown_dotfix(m):
		url, = m.groups()
		if ignore_trailing_dot and url.endswith("."):
			return "<{}>.".format(url[:-1])
		else:
			return "<{}>".format(url)

	# return _markdown_urls_pat.sub(r"<\1>", s)
	return _markdown_urls_pat.sub(markdown_dotfix, s)
