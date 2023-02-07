import asyncio
import logging
from collections import deque
from datetime import datetime
from typing import Any, Deque, List, Optional, Set

import aiohttp

from .datetime import now
from .url import get_filename_from_url

logger = logging.getLogger(__name__)


class DownloadTask:
    def __init__(self, url: str, path: str = ".") -> None:
        self.url = url
        self.path = path
        self.downloaded = 0
        self.resumable = False
        self.dt_started: Optional[datetime] = None
        self.dt_finished = now()

    def __hash__(self):
        return hash((self.url, self.path))

    def start(self) -> None:
        logger.info("starting download")
        self.dt_started = now()

    def done(self) -> None:
        logger.info("finished download")
        self.dt_finished = now()


class DownloadManager:
    def __init__(self, concurrent_downloads: int = 3) -> None:
        self.loop = asyncio.get_event_loop()
        self.timeout = aiohttp.ClientTimeout(total=None, sock_read=60)
        self.session = aiohttp.ClientSession(loop=self.loop, timeout=self.timeout, auto_decompress=False)
        self.concurrent_downloads = concurrent_downloads
        # self.sem = asyncio.Semaphore(1000)
        self.chunksize = 1024 * 1024  # file write buffer

        self.queue: Deque[DownloadTask] = deque()
        self.active: Set[DownloadTask] = set()
        self.done: List[DownloadTask] = []
        self.error: List[DownloadTask] = []

    def status(self) -> str:
        total_active = sum(t.downloaded for t in self.active)
        total_done = sum(t.downloaded for t in self.done)
        total_error = sum(t.downloaded for t in self.error)

        return "Queued: {}, active: {}, done: {}, error: {}\nDownload active: {}, done: {}, error: {}".format(
            len(self.queue), len(self.active), len(self.done), len(self.error), total_active, total_done, total_error
        )

    def _enqueue(self, task: DownloadTask, priority: Any) -> None:
        self.queue.append(task)

    def _start(self, task: DownloadTask) -> Optional[asyncio.Task]:
        if task not in self.active:
            self.active.add(task)
            atask = asyncio.ensure_future(self._download(task))
            return atask
        else:
            self.error.append(task)
            return None

    def _trystart(self) -> Optional[asyncio.Task]:
        if len(self.active) < self.concurrent_downloads:
            try:
                task = self.queue.popleft()
                return self._start(task)
            except IndexError:
                if not self.active:
                    logger.info("all done")
                    # self.loop.stop()
                    # task = asyncio.ensure_future(self._close())

        return None

    async def _download(self, task: DownloadTask) -> None:
        task.start()
        # await asyncio.sleep(10)

        # send http head request first to check for range support

        try:
            # async with self.session.get(task.url, headers={"Range": "bytes=0-10"}) as response:
            async with self.session.get(task.url, headers={}) as response:
                stream = response.content
                try:
                    size: Optional[int] = int(response.headers.get("content-length", ""))
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
            self.error.append(task)
        else:
            self.done.append(task)

        task.done()
        self.active.remove(task)
        self._trystart()

    def download(
        self, url: str, path: Optional[str] = None, priority: int = 0, force: bool = False
    ) -> Optional[asyncio.Task]:
        path = path or get_filename_from_url(url)
        logger.info("Starting download <%s> to <%s>", url, path)
        task = DownloadTask(url, path)
        if force:
            return self._start(task)
        else:
            self._enqueue(task, priority)
            return self._trystart()

    async def _close(self) -> None:
        await self.session.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    import wx
    from wxasync import AsyncBind, StartCoroutine, WxAsyncApp

    DOWNLOAD_URL = "http://releases.ubuntu.com/18.04.3/ubuntu-18.04.3-live-server-amd64.iso"

    class TestFrame(wx.Frame):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.dm = DownloadManager()

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
            self.dm.download(DOWNLOAD_URL)
            self.edit.SetLabel("WX COMPLETE")

        async def update_clock(self):
            while True:
                self.edit_timer.SetLabel(self.dm.status())
                await asyncio.sleep(0.5)

    async def main():
        app = WxAsyncApp()
        frame = TestFrame()
        frame.Show()
        app.SetTopWindow(frame)
        await app.MainLoop()

    loop = asyncio.events.new_event_loop()
    try:
        asyncio.events.set_event_loop(loop)
        loop.run_until_complete(main())
    finally:
        asyncio.events.set_event_loop(None)
        loop.close()
