from __future__ import generator_stop

import errno
import gzip
import json
import logging
import os
import os.path
import socket
import ssl
from email.utils import parsedate_to_datetime
from typing import IO, TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple, Union
from urllib import request
from urllib.error import URLError

from .exceptions import DownloadFailed
from .file import Tell, copyfilelike
from .filesystem import safe_filename
from .iter import first_not_none
from .url import get_filename_from_url

if TYPE_CHECKING:
    from email.message import Message
    from http.client import HTTPMessage
    from http.cookiejar import CookieJar

    JsonObject = Union[List[Any], Dict[str, Any]]

logger = logging.getLogger(__name__)
DEFAULT_TIMEOUT = 120.0


def install_ceritfi_opener() -> None:
    import certifi

    logger.warning("Using certifi store: %s", certifi.where())

    context = ssl.SSLContext()
    context.verify_mode = ssl.CERT_REQUIRED
    context.load_verify_locations(certifi.where())
    context.check_hostname = True
    https_handler = request.HTTPSHandler(context=context)
    opener = request.build_opener(https_handler)
    request.install_opener(opener)


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


def parsedate_to_timestamp(datestr: str) -> float:
    return parsedate_to_datetime(datestr).timestamp()


def get_filename(headers: "Message") -> Optional[str]:
    return headers.get_filename()


class URLRequestBuilder:
    def __init__(
        self, cookiejar: Optional["CookieJar"] = None, basicauth: Optional[Tuple[str, str, str]] = None
    ) -> None:

        handlers: List[request.BaseHandler] = []

        if cookiejar:
            handlers.append(request.HTTPCookieProcessor(cookiejar))
        if basicauth:
            top_level_url, username, password = basicauth
            password_mgr = request.HTTPPasswordMgrWithDefaultRealm()
            password_mgr.add_password(None, top_level_url, username, password)
            handlers.append(request.HTTPBasicAuthHandler(password_mgr))

        if handlers:
            opener = request.build_opener(*handlers)
            self.openfunc: Callable = opener.open
        else:
            self.openfunc = request.urlopen

    def getfunc(self):
        return self.openfunc

    def request(
        self,
        url: str,
        headers: Optional[dict] = None,
        timeout: float = DEFAULT_TIMEOUT,
        context: Optional[ssl.SSLContext] = None,
    ) -> "URLRequest":
        return URLRequest(url, headers, timeout, context, openfunc=self.openfunc)


class FileLike:
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

    def close(self) -> None:
        self.fp.close()

        transferred = self.response.tell()  # is this correct?
        if self.content_length is not None and self.content_length != transferred:
            raise ContentInvalidLength(None, self.content_length, transferred)

    def __enter__(self) -> IO[bytes]:
        return self.fp

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()


def get_redirect_url(url, headers=None):

    import requests

    r = requests.get(url, allow_redirects=False, headers=headers)
    r.raise_for_status()

    try:
        if r.status_code in {301, 302, 303, 307, 308}:
            return r.headers["Location"]
        else:
            raise NoRedirect(f"Unexpected status code: {r.status_code}", response=r)

    except KeyError:  # Location not provided. is this really raised?
        raise HTTPError("Location header not found", response=r)


class URLRequest:

    headers: "HTTPMessage"

    def __init__(
        self,
        url: str,
        headers: Optional[dict] = None,
        timeout: float = DEFAULT_TIMEOUT,
        context: Optional[ssl.SSLContext] = None,
        cookiejar: Optional["CookieJar"] = None,
        basicauth: Optional[Tuple[str, str, str]] = None,
        openfunc: Optional[Callable] = None,
    ) -> None:

        self.url = url
        self.timeout = timeout
        headers = headers or {}

        if not openfunc:
            openfunc = URLRequestBuilder(cookiejar, basicauth).getfunc()

        req = request.Request(url, data=None, headers=headers)
        self.response = openfunc(req, timeout=timeout, context=context)
        self.headers = self.response.info()

    def _close(self):  # unused
        self.response.close()

    def __enter__(self) -> "URLRequest":

        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.response.close()

    def _content_length(self) -> Optional[int]:

        try:
            content_length = self.headers["Content-Length"]
            return int(content_length)
        except (KeyError, ValueError, TypeError):
            return None

    def _last_modified(self) -> Optional[float]:

        try:
            last_modified = self.headers["Last-Modified"]
            return parsedate_to_timestamp(last_modified)
        except (KeyError, TypeError, ValueError):
            return None

    def get_redirect_url(self) -> str:
        self.response.close()
        return self.response.geturl()

    def _load(self) -> bytes:

        with FileLike(self) as fp:
            try:
                return fp.read()
            except URLError:
                raise TimeOut(f"Timed out after {self.timeout}s", response=self.response)

    def _json(self) -> "JsonObject":

        with FileLike(self) as fp:
            try:
                return json.load(fp)
            except URLError:
                raise TimeOut(f"Timed out after {self.timeout}s", response=self.response)

    def _download(
        self,
        basepath: str,
        filename: Optional[str] = None,
        fn_prio: Optional[Tuple[int, int, int, int]] = None,
        overwrite: bool = False,
        suffix: str = ".partial",
        report: Optional[Callable[[int, int], None]] = None,
    ) -> Tuple[Optional[int], str]:

        """PermissionError: [WinError 32] Der Prozess kann nicht auf die Datei zugreifen,
        da sie von einem anderen Prozess verwendet wird:
        'G:\\PUBLIC\\Audio\\Podcasts\\Radio Nukular\\radio_nukular_057.m4a.partial'
        -> 'G:\\PUBLIC\\Audio\\Podcasts\\Radio Nukular\\radio_nukular_057.m4a'
        """

        logger.debug("Downloading %s to %s", self.url, basepath)

        if fn_prio is None:
            fn_prio = (0, 1, 2, 3)

        filenames_ = {
            0: filename,
            1: get_filename(self.headers),
            2: get_filename_from_url(self.response.geturl()),  # url after redirect
            3: get_filename_from_url(self.url),
        }

        filenames = [filenames_[p] for p in fn_prio]
        logger.info("Filenames: {}".format(", ".join(map(str, filenames))))

        filename = first_not_none(filenames)

        if not filename:
            raise ValueError("Please provide a filename")

        filename = safe_filename(filename)
        fullpath = os.path.join(basepath, filename)
        tmppath = fullpath + suffix

        if not overwrite and os.path.exists(fullpath):
            raise FileExistsError(errno.EEXIST, "File already exists", fullpath)

        os.makedirs(basepath, exist_ok=True)

        content_length = self._content_length()

        try:
            # actually download the file
            with open(tmppath, "wb") as out:
                # https://www.ietf.org/mail-archive/web/httpbisa/current/msg27484.html
                transferred = copyfilelike(self.response, out, content_length, report=report)

        except (socket.timeout, URLError):
            logger.warning(f"Timeout after {self.timeout}s at {self.response.geturl()}: {self.headers}")
            raise TimeOut(f"Timed out after {self.timeout}s", response=self.response)

        except ConnectionResetError as e:
            logger.warning("Connection was reset during download: %s", str(e))
            raise DownloadInterrupted("Connection was reset during download")

        except Exception:
            logger.exception("Downloading failed mid file. Handle.")
            raise

        if content_length and content_length != transferred:
            logger.info(f"{content_length} {transferred}")
            raise ContentInvalidLength(tmppath, content_length, transferred)

        last_modified = self._last_modified()
        if last_modified:
            os.utime(tmppath, (-1, last_modified))

        os.rename(tmppath, fullpath)

        return (content_length, filename)

    def load(self) -> bytes:

        try:
            return self._load()
        finally:
            self.response.close()

    def json(self) -> "JsonObject":

        try:
            return self._json()
        finally:
            self.response.close()

    def download(
        self,
        basepath: str,
        filename: Optional[str] = None,
        fn_prio: Optional[Tuple[int, int, int, int]] = None,
        overwrite: bool = False,
        suffix: str = ".partial",
        report: Optional[Callable[[int, int], None]] = None,
    ) -> Tuple[Optional[int], str]:

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
