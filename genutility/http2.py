from itertools import count
from socket import timeout as SocketTimeout
from ssl import SSLContext
from time import sleep
from typing import Dict, Optional

from hyper import HTTP20Connection
from hyper.http20.exceptions import StreamResetError

from .http import HTTPError


class WrappedHTTP20Connection:
    def __init__(self, host: str, secure: Optional[bool] = None, ssl_context: Optional[SSLContext] = None) -> None:
        self.host = host
        self.secure = secure
        self.ssl_context = ssl_context

    def connect(self) -> None:
        self.conn = HTTP20Connection(self.host, secure=self.secure, ssl_context=self.ssl_context)

    def _dl_url(self, path: str, headers: Optional[Dict[str, str]], timeout: float) -> bytes:
        self.conn.request("GET", path, headers=headers)
        self.conn._sock._sck.settimeout(timeout)
        resp = self.conn.get_response()
        if resp.status >= 200 and resp.status < 300:
            return resp.read()

        print(path, resp.status, resp.trailers, resp.headers)
        raise HTTPError("non-2xx error", response=resp)

    def dl_url(self, path: str, headers: Optional[Dict[str, str]] = None, timeout: float = 60) -> bytes:
        for i in count(1):
            sleep(i)
            try:
                return self._dl_url(path, headers, timeout)
            except (ConnectionResetError, SocketTimeout, StreamResetError):
                self.connect()
                continue
