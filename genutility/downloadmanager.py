from __future__ import absolute_import, division, print_function, unicode_literals

import logging, asyncio
from typing import TYPE_CHECKING

import aiohttp
from orderedset import OrderedSet

from .datetime import now

if TYPE_CHECKING:
	from typing import Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DownloadTask(object):

	def __init__(self, url, path="."):
		self.url = url
		self.path = path
		self.downloaded = 0
		self.resumable = False
		self.dt_started = None
		self.dt_finished = now()

	def __hash__(self):
		return hash((self.url, self.path))

	def start(self):
		logger.info("starting download")
		self.dt_started = now()

	def done(self):
		logger.info("finished download")
		self.dt_finished = now()

class DownloadManager(object):

	def __init__(self):
		self.loop = asyncio.get_event_loop()
		self.timeout = aiohttp.ClientTimeout(total=60)
		self.session = aiohttp.ClientSession(loop=self.loop, timeout=self.timeout, auto_decompress=False)
		self.concurrent_downloads = 3
		#self.sem = asyncio.Semaphore(1000)
		self.chunksize = 1024*1024 # file write buffer

		self.queue = OrderedSet()
		self.active = OrderedSet()
		self.done = OrderedSet()

	def status(self):
		return "Queued: {}, active: {}, done: {}".format(len(self.queue), len(self.active), len(self.done))

	def _enqueue(self, task, priority):
		self.queue.add(task)

	def _start(self, task):
		self.active.add(task)
		task = asyncio.ensure_future(self._download(task))
		return task

	def _trystart(self):
		if len(self.active) < self.concurrent_downloads:
			try:
				task = self.queue.pop()
				self._start(task)
			except KeyError:
				if not self.active:
					logger.info("all done")
					#self.loop.stop()
					#task = asyncio.ensure_future(self._close())

	async def _download(self, task):
		task.start()
		#await asyncio.sleep(10)

		# send http head request first to check for range support
		
		#async with self.session.get(task.url, headers={"Range": "bytes=0-10"}) as response:
		async with self.session.get(task.url, headers={}) as response:
			stream = response.content
			try:
				size = int(response.headers.get('content-length'))
			except (ValueError, TypeError):
				size = None

			accept_range = response.headers.get('Accept-Ranges', 'none').lower()
			print(accept_range)

			if response.status == 200: # range not supported
				pass
			elif response.status == 206: # range supported
				assert accept_range == "bytes"
				bytes_range = response.headers.get('Content-Range') # 'bytes 0-10/46239'

			with open(task.path, "wb", buffering=self.chunksize) as fd:
				async for data in stream.iter_any():
					task.downloaded += len(data)
					fd.write(data)

			if size and size != task.downloaded:
				print("incomplete", task.downloaded, "of", size)

		task.done()

		self.active.remove(task)
		self.done.add(task)
		self._trystart()

	def download(self, url, path="tmp.txt", priority=0, force=False):
		logger.info("starting download")
		task = DownloadTask(url, path)
		if force:
			self._start(task)
		else:
			self._enqueue(task, priority)
			self._trystart()

	async def _close(self):
		await self.session.close()

if __name__ == "__main__":

	dm = DownloadManager()

	import wx
	from wxasync import AsyncBind, WxAsyncApp, StartCoroutine
	from asyncio.events import get_event_loop
	import time

	class TestFrame(wx.Frame):
		def __init__(self, parent=None):
			super(TestFrame, self).__init__(parent)
			vbox = wx.BoxSizer(wx.VERTICAL)
			button1 =  wx.Button(self, label="Submit")
			self.edit =  wx.StaticText(self, style=wx.ALIGN_CENTRE_HORIZONTAL|wx.ST_NO_AUTORESIZE)
			self.edit_timer =  wx.StaticText(self, style=wx.ALIGN_CENTRE_HORIZONTAL|wx.ST_NO_AUTORESIZE)
			vbox.Add(button1, 2, wx.EXPAND|wx.ALL)
			vbox.AddStretchSpacer(1)
			vbox.Add(self.edit, 1, wx.EXPAND|wx.ALL)
			vbox.Add(self.edit_timer, 1, wx.EXPAND|wx.ALL)
			self.SetSizer(vbox)
			self.Layout()
			AsyncBind(wx.EVT_BUTTON, self.async_callback, button1)
			StartCoroutine(self.update_clock, self)

		async def async_callback(self, event):
			self.edit.SetLabel("WX WAITING")
			dm.download("http://google.com") # doesn't support range
			#dm.download("https://curl.haxx.se/docs/manpage.html") # supports range
			self.edit.SetLabel("WX COMPLETE")

		async def update_clock(self):
			while True:
				self.edit_timer.SetLabel(dm.status())
				await asyncio.sleep(0.5)

	app = WxAsyncApp()
	frame = TestFrame()
	frame.Show()
	app.SetTopWindow(frame)
	loop = get_event_loop()
	loop.run_until_complete(app.MainLoop())
