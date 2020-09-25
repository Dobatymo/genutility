from __future__ import absolute_import, division, print_function, unicode_literals

from builtins import map, str
from future.moves.urllib import request
from future.moves.urllib.error import URLError

import errno
import gzip
import json
import logging
import os
import os.path
import socket
from io import open
from typing import TYPE_CHECKING

from .compat import FileExistsError
from .exceptions import DownloadFailed
from .file import Tell, copyfilelike
from .filesystem import safe_filename
from .iter import first_not_none
from .url import get_filename_from_url

if TYPE_CHECKING:
	from http.client import HTTPMessage
	from http.cookiejar import CookieJar
	from typing import Callable, Mapping, Optional, Tuple

if __debug__:
	import requests

logger = logging.getLogger(__name__)

class HTTPError(Exception):

	def __init__(self, *args, **kwargs):
		response = kwargs.pop("response", None)
		Exception.__init__(self, *args, **kwargs)
		self.response = response

class ContentInvalidLength(HTTPError, DownloadFailed):

	def __init__(self, path, expected, received):
		HTTPError.__init__(self, path, expected, received)

class TimeOut(HTTPError, DownloadFailed):
	pass

class DownloadInterrupted(HTTPError, DownloadFailed):
	pass

class NoRedirect(HTTPError):
	pass

try:
	from email.utils import parsedate_to_datetime  # new in 3.3

	def parsedate_to_timestamp(datestr): # correct timezone
		return parsedate_to_datetime(datestr).timestamp()

except ImportError:
	import time

	def parsedate_to_timestamp(datestr): # fixme: incorrect timezone
		# type: (str, ) -> float

		try:
			#str fixed py2.x unicode bug
			return time.mktime(time.strptime(datestr, str("%a, %d %b %Y %H:%M:%S %Z")))
		except ValueError:
			#time data 'Thu, 02 Aug 2007 06:54:23 GMT' does not match format u'%a, %d %b %Y %H:%M:%S +0000' # fixed with str()
			return time.mktime(time.strptime(datestr, str("%a, %d %b %Y %H:%M:%S +0000")))

try:
	from email.message import EmailMessage  # new in 3.6

	def get_filename(headers):
		# type: (EmailMessage, ) -> str

		return headers.get_filename()

except ImportError:
	def get_filename(headers):
		# type: (Mapping, ) -> str

		try:
			content_disposition = headers["Content-Disposition"]
			return content_disposition.split("=")[1].replace("\"", "").strip()
		except (KeyError, IndexError):
			return None

class URLRequestBuilder(object):

	def __init__(self, cookiejar=None, basicauth=None):
		# type: (Optional[CookieJar], Optional[Tuple[str, str, str]]) -> None

		handlers = []

		if cookiejar:
			handlers.append(request.HTTPCookieProcessor(cookiejar))
		if basicauth:
			top_level_url, username, password = basicauth
			password_mgr = request.HTTPPasswordMgrWithDefaultRealm()
			password_mgr.add_password(None, top_level_url, username, password)
			handlers.append(request.HTTPBasicAuthHandler(password_mgr))

		if handlers:
			opener = request.build_opener(handlers)
			self.openfunc = opener.open
		else:
			self.openfunc = request.urlopen

	def getfunc(self):
		return self.openfunc

	def request(self, url, headers=None, timeout=None):
		return URLRequest(url, headers, timeout, openfunc=self.openfunc)

class FileLike(object):

	def __init__(self, urlrequest):
		self.urlrequest = urlrequest

		self.content_length = self.urlrequest._content_length()

		self.response = Tell(self.urlrequest.response)
		if self.urlrequest.headers.get("Content-Encoding", None) == "gzip":
			# if that does not work, use BytesIO
			logger.info("Using gzip")
			self.fp = gzip.GzipFile(fileobj=self.response)
		else:
			self.fp = self.response

	def close(self):
		self.fp.close()

		transferred = self.response.tell() # is this correct?
		if self.content_length is not None and self.content_length != transferred:
			raise ContentInvalidLength(None, self.content_length, transferred)

	def __enter__(self):
		return self.fp

	def __exit__(self, exc_type, exc_value, traceback):
		self.close()

def get_redirect_url(url, headers=None):

	import requests

	r = requests.get(url, allow_redirects=False, headers=headers)
	r.raise_for_status()

	try:
		if r.status_code in {301, 302, 303, 307, 308}:
			return r.headers["Location"]
		else:
			raise NoRedirect("Unexpected status code: {}".format(r.status_code), response=r)

	except KeyError: # Location not provided. is this really raised?
		raise HTTPError("Location header not found", response=r)

class URLRequest(object):

	def __init__(self, url, headers=None, timeout=120, cookiejar=None, basicauth=None, openfunc=None):
		# type: (str, Optional[dict], Optional[float], Optional[CookieJar], Optional[Tuple[str, str, str]], Optional[Callable]) -> None

		self.url = url
		self.timeout = timeout
		headers = headers or {}

		if not openfunc:
			openfunc = URLRequestBuilder(cookiejar=None, basicauth=None).getfunc()

		req = request.Request(url, data=None, headers=headers)
		self.response = openfunc(req, timeout=timeout)
		self.headers = self.response.info() # type: HTTPMessage

	def _close(self): # unused
		self.response.close()

	def __enter__(self):
		# type: () -> URLRequest

		return self

	def __exit__(self, exc_type, exc_value, traceback):
		self.response.close()

	def _content_length(self):
		# type: () -> Optional[int]

		try:
			content_length = self.headers["Content-Length"]
			return int(content_length)
		except (KeyError, ValueError, TypeError):
			return None

	def _last_modified(self):
		# type: () -> Optional[float]

		try:
			last_modified = self.headers["Last-Modified"]
			return parsedate_to_timestamp(last_modified)
		except (KeyError, TypeError, ValueError):
			return None

	def get_redirect_url(self):
		self.response.close()
		return self.response.geturl()

	def _load(self):
		# type: () -> bytes

		with FileLike(self) as fp:
			try:
				return fp.read()
			except URLError:
				raise TimeOut("Timed out after {}s".format(self.timeout), response=self.response)

	def _json(self):
		# type: () -> dict

		with FileLike(self) as fp:
			try:
				return json.load(fp)
			except URLError:
				raise TimeOut("Timed out after {}s".format(self.timeout), response=self.response)

	def _download(self, basepath, filename=None, fn_prio=None, overwrite=False, suffix=".partial", report=None):
		# type: (str, Optional[str], Optional[Tuple[int, int, int, int]], bool, str, Optional[Callable[[int, int], None]]) -> Tuple[Optional[int], str]

		"""PermissionError: [WinError 32] Der Prozess kann nicht auf die Datei zugreifen,
			da sie von einem anderen Prozess verwendet wird:
			'G:\\PUBLIC\\Audio\\Podcasts\\Radio Nukular\\radio_nukular_057.m4a.partial'
			-> 'G:\\PUBLIC\\Audio\\Podcasts\\Radio Nukular\\radio_nukular_057.m4a'
		"""

		logger.debug("Downloading %s to %s", self.url, basepath)

		if fn_prio is None:
			fn_prio = (0, 1, 2, 3)

		filenames = {
			0: filename,
			1: get_filename(self.headers),
			2: get_filename_from_url(self.response.geturl()), # url after redirect
			3: get_filename_from_url(self.url),
		}

		filenames = [filenames[p] for p in fn_prio]
		logger.info("Filenames: {}".format(", ".join(map(str, filenames))))

		filename = first_not_none(filenames)

		if not filename:
			raise ValueError("Please provide a filename")

		filename = safe_filename(filename)
		fullpath = os.path.join(basepath, filename)
		tmppath = fullpath + suffix

		if not overwrite and os.path.exists(fullpath):
			raise FileExistsError(errno.EEXIST, "File already exists", fullpath)

		try:
			os.makedirs(basepath) # exist_ok=True is new in 3.2
		except OSError:
			pass

		content_length = self._content_length()

		try:
			# actually download the file
			with open(tmppath, "wb") as out:
				# https://www.ietf.org/mail-archive/web/httpbisa/current/msg27484.html
				transferred = copyfilelike(self.response, out, content_length, report=report)

		except (socket.timeout, URLError):
			logger.warning("Timeout after {}s at {}: {}".format(self.timeout, self.response.geturl(), self.headers))
			raise TimeOut("Timed out after {}s".format(self.timeout), response=self.response)

		except ConnectionResetError as e:
			logger.warning("Connection was reset during download: %s", str(e))
			raise DownloadInterrupted("Connection was reset during download")

		except Exception as e:
			logger.exception("Downloading failed mid file. Handle.")
			raise

		if content_length and content_length != transferred:
			logger.info("{} {}".format(content_length, transferred))
			raise ContentInvalidLength(tmppath, content_length, transferred)

		last_modified = self._last_modified()
		if last_modified:
			os.utime(tmppath, (-1, last_modified))

		os.rename(tmppath, fullpath)

		return (content_length, filename)

	def load(self):
		# type: () -> bytes

		try:
			return self._load()
		finally:
			self.response.close()

	def json(self):
		# type: () -> bytes

		try:
			return self._json()
		finally:
			self.response.close()

	def download(self, basepath, filename=None, fn_prio=None, overwrite=False, suffix=".partial", report=None):
		# type: () -> Tuple[Optional[int], str]

		try:
			return self._download(basepath, filename, fn_prio, overwrite, suffix, report)
		finally:
			self.response.close()

if __name__ == "__main__":
	from argparse import ArgumentParser

	parser = ArgumentParser(description="Downloads url to file")
	parser.add_argument("url", help="url to download")
	parser.add_argument("dir", help="output directory")
	parser.add_argument("-f", "--filename", help="filename")
	args = parser.parse_args()

	URLRequest(args.url).download(args.dir, args.filename)
