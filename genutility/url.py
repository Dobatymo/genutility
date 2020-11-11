from __future__ import absolute_import, division, print_function, unicode_literals

from future.moves.urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

import os.path
import re
from string import ascii_letters, digits
from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from future.moves.urllib.parse import SplitResult

	from typing import Dict, Iterable, Optional

# URI RFC
gen_delims = ":/?#[]@"
sub_delims = "!$&'()*+;="
reserved = gen_delims + sub_delims
unreserved = ascii_letters + digits + "-._~"
valid_uri_characters = reserved + unreserved

uri_schemes = ("http", "https", "ftp", "sftp", "irc", "magnet", "file", "data")
url_base_pattern = r"(?:(?:{}:\/\/)|www\.)(?:[{}]|%[a-zA-Z0-9]{{2}})+"

def get_url_pattern(schemes=None):
	# type: (Optional[Iterable[str]], ) -> re.Pattern

	schemes = schemes or uri_schemes
	return re.compile(url_base_pattern.format("|".join(schemes), re.escape(valid_uri_characters)))

def get_filename_from_url(url, strip=None):
	# type: (str, Optional[str]) -> str

	return urlsplit(url).path.rstrip(strip).rsplit("/", 1)[1]

def get_url_argument(split_url, argument, path=None):
	# type: (SplitResult, str, Optional[str]) -> Optional[str]

	""" Extracts a parameter value from the url query string. Optionally compares the url path.
		For example:
		> get_url_argument(urlsplit("https://www.google.com/search?q=python"), "q")
		'python'
	"""

	if not path or split_url.path == path:
		try:
			return parse_qs(split_url.query)[argument][0]
		except KeyError:
			return None
	return None

def url_replace_query(split_url, query, drop_fragment=True):
	# type: (SplitResult, Dict[str, str], bool) -> str

	""" Replace the query part of an URL with a new one.
		For example:
		> url_replace_query(urlsplit("https://www.google.com/search?source=hp&q=java"), {"q": "python"})
		'https://www.google.com/search?q=python'
	"""

	scheme, netloc, path, _, fragment = split_url

	query = urlencode(query)
	if drop_fragment:
		fragment = ""

	return urlunsplit((scheme, netloc, path, query, fragment))

def path_ext(path):
	return os.path.splitext(path)[1][1:].lower()

def url_ext(url):
	# type: (str, ) -> str

	""" Returns the lowercase file extension of the URI/URL. """

	path = urlsplit(url).path
	return path_ext(path)
