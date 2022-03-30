from __future__ import generator_stop

import asyncio
import sys
from numbers import Number
from time import time
from typing import Iterable, Optional, Sequence, TextIO, Union

from .iter import _lstr, progressdata


class progress_content:
    def __init__(
        self,
        it: Union[Iterable, Sequence],
        length: Optional[int] = None,
        refresh: Number = 1,
        file: Optional[TextIO] = sys.stdout,
    ) -> None:

        self.it = it
        self.length = length
        self.refresh = refresh
        self.file = file

    def __iter__(self):
        return progressdata(self.it, self.length, self.refresh, file=self.file)

    def __aiter__(self):
        return self.AsyncIterProgress(self.it, self.length, self.refresh, file=self.file)

    class AsyncIterProgress:
        def __init__(
            self, it: Union[Iterable, Sequence], length: Optional[int], refresh: Number, file: Optional[TextIO]
        ):
            self.it = it.__aiter__()
            self.refresh = refresh
            self.file = file

            self.length, self.lstr = _lstr(self.it, length)
            self.last = self.start = time()
            self.total = 0

        @asyncio.coroutine
        def __anext__(self):
            try:
                elm = yield from self.it.__anext__()
                self.total += len(elm)
                current = time()
                if current - self.last > self.refresh:
                    self.last = current
                    duration = current - self.start
                    print(
                        f"{self.total}{self.lstr}, running for {int(duration)} seconds ({self.total/duration:0.2e}/s).",
                        end="\r",
                        file=self.file,
                    )
                return elm

            except StopAsyncIteration:
                print(f"Finished {self.total} in {int(self.last - self.start)} seconds.", end="\r", file=self.file)
                raise StopAsyncIteration


if __name__ == "__main__":

    class gensync:
        def __init__(self):
            self.i = 3

        def __iter__(self):
            return self

        def __next__(self):
            if self.i > 0:
                self.i -= 1
                return "asd"
            else:
                raise StopIteration

    class genasync:
        def __init__(self):
            self.i = 3

        def __aiter__(self):
            return self

        @asyncio.coroutine
        def __anext__(self):
            if self.i > 0:
                self.i -= 1
                return "asd"
            else:
                raise StopAsyncIteration

    for i in progress_content(gensync()):
        pass

    print()

    @asyncio.coroutine
    async def run():
        async for i in progress_content(genasync()):
            pass

    loop = asyncio.get_event_loop()
    loop.run_until_complete(run())
    loop.close()
