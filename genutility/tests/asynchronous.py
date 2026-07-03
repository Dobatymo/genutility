import sys
from unittest import IsolatedAsyncioTestCase, skipIf


@skipIf(sys.version_info < (3, 9), "requires Python 3.9+")
class ProgressContentTest(IsolatedAsyncioTestCase):
    def test_sync(self):
        from genutility.asynchronous import progress_content

        self.assertEqual([b"a", b"bb"], list(progress_content([b"a", b"bb"], file=None)))

    async def test_async(self):
        from genutility.asynchronous import progress_content

        async def gen():
            yield b"a"
            yield b"bb"

        self.assertEqual([b"a", b"bb"], [item async for item in progress_content(gen(), file=None)])


if __name__ == "__main__":
    import unittest

    unittest.main()
