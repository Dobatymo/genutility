from __future__ import generator_stop

from itertools import count
from socket import timeout as SocketTimeout
from time import sleep
from typing import Optional

from hyper import HTTP20Connection
from hyper.http20.exceptions import StreamResetError

from .http import HTTPError


class WrappedHTTP20Connection:
    def __init__(self, host: str) -> None:
        self.host = host

    def connect(self) -> None:
        self.conn = HTTP20Connection(self.host)

    def _dl_url(self, path: str, headers: Optional[dict], timeout: float):
        self.conn.request("GET", path, headers=headers)
        self.conn._sock._sck.settimeout(timeout)
        resp = self.conn.get_response()
        if resp.status >= 200 and resp.status < 300:
            return resp.read()

        print(path, resp.status, resp.trailers, resp.headers)
        raise HTTPError("non-2xx error", response=resp)

    def dl_url(self, path: str, headers: Optional[dict] = None, timeout: float = 60):
        for i in count(1):
            sleep(i)
            try:
                return self._dl_url(path, headers, timeout)
            except (ConnectionResetError, SocketTimeout, StreamResetError):
                self.connect()
                continue
