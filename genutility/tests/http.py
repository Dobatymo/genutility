from email.message import Message
from io import BytesIO

from genutility.http import URLRequest
from genutility.test import MyTestCase


class Response(BytesIO):
    def __init__(self, data, headers):
        super().__init__(data)
        self.headers = headers

    def info(self):
        return self.headers

    def geturl(self):
        return "https://example.invalid/file"

    def seekable(self):
        return False


class HttpTest(MyTestCase):
    def test_urlrequest_load(self):
        headers = Message()
        headers["Content-Length"] = "5"
        response = Response(b"hello", headers)
        request = URLRequest("https://example.invalid", openfunc=lambda *args, **kwargs: response)

        self.assertEqual(b"hello", request.load())
        self.assertTrue(response.closed)


if __name__ == "__main__":
    import unittest

    unittest.main()
