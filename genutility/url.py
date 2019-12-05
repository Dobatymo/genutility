from __future__ import absolute_import, division, print_function, unicode_literals

from future.moves.urllib.parse import urlsplit, urlparse
import re
from string import ascii_letters, digits

# URI RFC
gen_delims = ":/?#[]@"
sub_delims = "!$&'()*+;="
reserved = gen_delims + sub_delims
unreserved = ascii_letters + digits + "-._~"
valid_uri_characters = reserved + unreserved

uri_schemes = ("http", "https", "ftp", "sftp", "irc", "magnet", "file", "data")
url_base_pattern = r"(?:(?:{}:\/\/)|www\.)(?:[{}]|%[a-zA-Z0-9]{{2}})+"

def get_url_pattern(schemes=None):
	schemes = schemes or uri_schemes
	return re.compile(url_base_pattern.format("|".join(schemes), re.escape(valid_uri_characters)))

def get_filename_from_url(url):
	return url.rstrip("/").rsplit("/", 1)[1]

def get_filename_from_url_v2(url):
	return urlparse(url)[2].split("/")[-1]

def get_filename_from_url_v3(url):
	return os.path.split(urlsplit(url).path)[1]
