from __future__ import absolute_import, division, print_function, unicode_literals

from itertools import count
from socket import timeout as SocketTimeout
from time import sleep

from hyper import HTTP20Connection
from hyper.http20.exceptions import StreamResetError

from .http import HTTPError


class WrappedHTTP20Connection(object):

	def __init__(self, host):
		self.host = host

	def connect(self):
		self.conn = HTTP20Connection(self.host)

	def _dl_url(self, path, headers, timeout):
		self.conn.request("GET", path, headers=headers)
		self.conn._sock._sck.settimeout(timeout)
		resp = self.conn.get_response()
		if resp.status >= 200 and resp.status < 300:
			return resp.read()

		print(path, resp.status, resp.trailers, resp.headers)
		raise HTTPError("non-2xx error", response=resp)

	def dl_url(self, path, headers=None, timeout=60):
		for i in count(1):
			sleep(i)
			try:
				return self._dl_url(path, headers, timeout)
			except (ConnectionResetError, SocketTimeout, StreamResetError) as e:
				self.connect()
				continue

