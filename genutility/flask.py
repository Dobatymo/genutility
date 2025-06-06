from base64 import urlsafe_b64decode, urlsafe_b64encode
from typing import Dict, Hashable, Optional, TypeVar
from urllib.parse import quote, unquote

from flask import Response, request
from werkzeug.routing import BaseConverter

T = TypeVar("T")
H = TypeVar("H", bound=Hashable)

""" examples

user_dict = {
    "username": "password"
}

@before_request
def auth():
    return do_basic_auth(user_dict)

"""


class Base64Converter(BaseConverter):
    def to_python(self, value: str) -> str:  # decode once as the wsgi app already receives a decoded url
        return urlsafe_b64decode(value.encode("ascii")).decode("utf-8")

    def to_url(self, value: str) -> str:
        return urlsafe_b64encode(value.encode("utf-8")).decode("ascii")


class DoubleQuoteConverter(BaseConverter):
    def to_python(self, value: str) -> str:  # decode once as the wsgi app already receives a decoded url
        return unquote(value)

    def to_url(self, value: str) -> str:
        return quote(quote(value, safe=""), safe="")


def check_auth(username: H, password: T, user_dict: Dict[H, T]) -> bool:
    try:
        return user_dict[username] == password
    except KeyError:
        return False


def authenticate() -> Response:
    """Sends a 401 response that enables basic auth"""

    return Response(
        "Could not verify your access level for that URL.\nYou have to login with proper credentials",
        401,
        {"WWW-Authenticate": 'Basic realm="Login Required"'},
    )


def do_basic_auth(user_dict: Dict[H, T]) -> Optional[Response]:
    auth = request.authorization
    if not auth or not check_auth(auth.username, auth.password, user_dict):
        return authenticate()
    else:
        return None
