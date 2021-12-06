from __future__ import generator_stop

import asyncio
import logging
from typing import TYPE_CHECKING

import aiohttp
from orderedset import OrderedSet

from .datetime import now

if TYPE_CHECKING:
    from typing import Any, Optional

    from .datetime import datetime

logger = logging.getLogger(__name__)


class DownloadTask:
    def __init__(self, url, path="."):
        # type: (str, str) -> None

        self.url = url
        self.path = path
        self.downloaded = 0
        self.resumable = False
        self.dt_started = None  # type: Optional[datetime]
        self.dt_finished = now()

    def __hash__(self):
        return hash((self.url, self.path))

    def start(self):
        # type: () -> None

        logger.info("starting download")
        self.dt_started = now()

    def done(self):
        # type: () -> None

        logger.info("finished download")
        self.dt_finished = now()


class DownloadManager:
    def __init__(self):
        # type: () -> None

        self.loop = asyncio.get_event_loop()
        self.timeout = aiohttp.ClientTimeout(total=None, sock_read=60)
        self.session = aiohttp.ClientSession(loop=self.loop, timeout=self.timeout, auto_decompress=False)
        self.concurrent_downloads = 3
        # self.sem = asyncio.Semaphore(1000)
        self.chunksize = 1024 * 1024  # file write buffer

        self.queue = OrderedSet()
        self.active = OrderedSet()
        self.done = OrderedSet()
        self.error = OrderedSet()

    def status(self):
        # type: () -> str

        total_active = sum(t.downloaded for t in self.active)
        total_done = sum(t.downloaded for t in self.done)
        total_error = sum(t.downloaded for t in self.error)

        return "Queued: {}, active: {}, done: {}, error: {}\nDownload active: {}, done: {}, error: {}".format(
            len(self.queue), len(self.active), len(self.done), len(self.error), total_active, total_done, total_error
        )

    def _enqueue(self, task, priority):
        # type: (DownloadTask, Any) -> None

        self.queue.add(task)

    def _start(self, task):
        # type: (DownloadTask, ) -> asyncio.Task

        self.active.add(task)
        atask = asyncio.ensure_future(self._download(task))
        return atask

    def _trystart(self):
        # type: () -> Optional[asyncio.Task]

        if len(self.active) < self.concurrent_downloads:
            try:
                task = self.queue.pop()
                return self._start(task)
            except KeyError:
                if not self.active:
                    logger.info("all done")
                    # self.loop.stop()
                    # task = asyncio.ensure_future(self._close())

        return None

    async def _download(self, task):
        # type: (DownloadTask, ) -> None

        task.start()
        # await asyncio.sleep(10)

        # send http head request first to check for range support

        try:

            # async with self.session.get(task.url, headers={"Range": "bytes=0-10"}) as response:
            async with self.session.get(task.url, headers={}) as response:
                stream = response.content
                try:
                    size = int(response.headers.get("content-length", ""))  # type: Optional[int]
                except (ValueError, TypeError):
                    size = None

                accept_range = response.headers.get("Accept-Ranges", "none").lower()

                if response.status == 200:  # range not supported
                    pass
                elif response.status == 206:  # range supported
                    if accept_range != "bytes":
                        raise RuntimeError("Only bytes content ranges are supported")
                    bytes_range = response.headers.get("Content-Range")  # 'bytes 0-10/46239'
                    raise RuntimeError(f"Range requests are not supported yet: {bytes_range}")

                with open(task.path, "wb", buffering=self.chunksize) as fw:
                    async for data in stream.iter_any():
                        task.downloaded += len(data)
                        fw.write(data)

                if size and size != task.downloaded:
                    print("incomplete", task.downloaded, "of", size)

        except asyncio.TimeoutError:
            self.error.add(task)
        else:
            self.done.add(task)

        task.done()
        self.active.remove(task)
        self._trystart()

    def download(self, url, path="tmp.txt", priority=0, force=False):
        # type: (str, str, int, bool) -> Optional[asyncio.Task]

        logger.info("starting download")
        task = DownloadTask(url, path)
        if force:
            return self._start(task)
        else:
            self._enqueue(task, priority)
            return self._trystart()

    async def _close(self):
        await self.session.close()


if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)

    dm = DownloadManager()

    from asyncio.events import get_event_loop

    import wx
    from wxasync import AsyncBind, StartCoroutine, WxAsyncApp

    DOWNLOAD_URL = "http://releases.ubuntu.com/18.04.3/ubuntu-18.04.3-live-server-amd64.iso"

    class TestFrame(wx.Frame):
        def __init__(self, parent=None):
            super().__init__(parent)
            vbox = wx.BoxSizer(wx.VERTICAL)
            button1 = wx.Button(self, label="Submit")
            self.edit = wx.StaticText(self, style=wx.ALIGN_CENTRE_HORIZONTAL | wx.ST_NO_AUTORESIZE)
            self.edit_timer = wx.StaticText(self, style=wx.ALIGN_CENTRE_HORIZONTAL | wx.ST_NO_AUTORESIZE)
            vbox.Add(button1, 2, wx.EXPAND | wx.ALL)
            vbox.AddStretchSpacer(1)
            vbox.Add(self.edit, 1, wx.EXPAND | wx.ALL)
            vbox.Add(self.edit_timer, 1, wx.EXPAND | wx.ALL)
            self.SetSizer(vbox)
            self.Layout()
            AsyncBind(wx.EVT_BUTTON, self.async_callback, button1)
            StartCoroutine(self.update_clock, self)

        async def async_callback(self, event):
            self.edit.SetLabel("WX WAITING")
            dm.download(DOWNLOAD_URL)
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
