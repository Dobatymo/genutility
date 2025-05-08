import sys
from collections.abc import AsyncIterator, Sized
from time import time
from typing import Generic, Iterable, Iterator, Optional, Sequence, TextIO, TypeVar, Union

from typing_extensions import Self

from .iter import _lstr, progressdata

SizedT = TypeVar("SizedT", bound=Sized)


class progress_content(Generic[SizedT]):
    def __init__(
        self,
        it: Union[Iterable[SizedT], Sequence[SizedT], AsyncIterator[SizedT]],
        length: Optional[int] = None,
        refresh: Union[int, float] = 1,
        file: Optional[TextIO] = sys.stdout,
    ) -> None:
        self.it = it
        self.length = length
        self.refresh = refresh
        self.file = file

    def __iter__(self) -> Iterator[SizedT]:
        assert not isinstance(self.it, AsyncIterator)
        return progressdata(self.it, self.length, self.refresh, file=self.file)

    def __aiter__(self) -> AsyncIterator[SizedT]:
        assert isinstance(self.it, AsyncIterator)
        return self.AsyncIterProgress(self.it, self.length, self.refresh, file=self.file)

    class AsyncIterProgress:
        def __init__(
            self, it: AsyncIterator[SizedT], length: Optional[int], refresh: Union[int, float], file: Optional[TextIO]
        ) -> None:
            self.it = it.__aiter__()
            self.refresh = refresh
            self.file = file

            self.length, self.lstr = _lstr(self.it, length)
            self.last = self.start = time()
            self.total = 0

        def __aiter__(self) -> Self:
            return self

        async def __anext__(self) -> SizedT:
            try:
                elm = await self.it.__anext__()
                self.total += len(elm)
                current = time()
                if current - self.last > self.refresh:
                    self.last = current
                    duration = current - self.start
                    print(
                        f"{self.total}{self.lstr}, running for {int(duration)} seconds ({self.total / duration:0.2e}/s).",
                        end="\r",
                        file=self.file,
                    )
                return elm

            except StopAsyncIteration:
                print(f"Finished {self.total} in {int(self.last - self.start)} seconds.", end="\r", file=self.file)
                raise StopAsyncIteration


if __name__ == "__main__":
    import asyncio

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

        async def __anext__(self):
            if self.i > 0:
                self.i -= 1
                return "asd"
            else:
                raise StopAsyncIteration

    for _i in progress_content(gensync()):
        pass

    print()

    async def main():
        async for _i in progress_content(genasync()):
            pass

    asyncio.run(main())
