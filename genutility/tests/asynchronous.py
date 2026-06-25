import asyncio
import sys
from unittest import skipIf

from genutility.test import MyTestCase


@skipIf(sys.version_info < (3, 9), "requires Python 3.9+")
class ProgressContentTest(MyTestCase):
    def test_sync(self):
        from genutility.asynchronous import progress_content

        self.assertEqual([b"a", b"bb"], list(progress_content([b"a", b"bb"], file=None)))

    def test_async(self):
        from genutility.asynchronous import progress_content

        async def gen():
            yield b"a"
            yield b"bb"

        async def collect():
            return [item async for item in progress_content(gen(), file=None)]

        self.assertEqual([b"a", b"bb"], asyncio.run(collect()))


if __name__ == "__main__":
    import unittest

    unittest.main()
