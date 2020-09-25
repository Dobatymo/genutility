from __future__ import absolute_import, division, print_function, unicode_literals

import asyncio
import sys
from time import time
from typing import TYPE_CHECKING

from .iter import _lstr, progressdata

# needs python 3.4


if TYPE_CHECKING:
	from numbers import Number
	from typing import IO, Iterable, Optional, Sequence, Union

class progress_content(object):

	def __init__(self, it, length=None, refresh=1, file=sys.stdout):
		# type: (Union[Iterable, Sequence], Optional[int], Number, Optional[IO[str]]) -> None

		self.it = it
		self.length = length
		self.refresh = refresh
		self.file = file

	def __iter__(self):
		return progressdata(self.it, self.length, self.refresh, file=self.file)

	def __aiter__(self):
		return self.AsyncIterProgress(self.it, self.length, self.refresh, file=self.file)

	class AsyncIterProgress(object):

		def __init__(self, it, length, refresh, file):
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
					print("{}{}, running for {} seconds ({:0.2e}/s).".format(self.total, self.lstr, int(duration), self.total/duration), end="\r", file=self.file)
				return elm

			except StopAsyncIteration:
				print("Finished {} in {} seconds.".format(self.total, int(self.last - self.start)), end="\r", file=self.file)
				raise StopAsyncIteration

if __name__ == "__main__":
	# needs python 3.5

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
