from __future__ import generator_stop

from typing import Any, Callable, Dict, Iterable, Mapping, Optional

from werkzeug.exceptions import BadRequest
from werkzeug.wsgi import get_host

WsgiApp = Any


class HostDispatcher:

    """Dispatch WSGI apps by host.
    app = HostDispatcher({'a.com': app_a, 'b.com': app_b})
    """

    def __init__(self, hosts: Dict[str, WsgiApp], default: Optional[WsgiApp] = None) -> None:

        self.hosts = hosts
        self.default = default or BadRequest()  # rfc7230#section-5.4

    def __call__(self, environ: Mapping[str, Any], start_response: Callable) -> Iterable[bytes]:

        host = get_host(environ)
        app = self.hosts.get(host, self.default)
        return app(environ, start_response)
