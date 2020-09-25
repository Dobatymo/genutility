from typing import TYPE_CHECKING

from werkzeug.exceptions import BadRequest
from werkzeug.wsgi import get_host

if TYPE_CHECKING:
	from typing import Any, Callable, Dict, Iterable, Mapping, Optional
	WsgiApp = Any

class HostDispatcher(object):

	""" Dispatch WSGI apps by host.
		app = HostDispatcher({'a.com': app_a, 'b.com': app_b})
	"""

	def __init__(self, hosts, default=None):
		# type: (Dict[str, WsgiApp], Optional[WsgiApp]) -> None

		self.hosts = hosts
		self.default = default or BadRequest() # rfc7230#section-5.4

	def __call__(self, environ, start_response):
		# type: (Mapping, Callable) -> Iterable[bytes]

		host = get_host(environ)
		app = self.hosts.get(host, self.default)
		return app(environ, start_response)
