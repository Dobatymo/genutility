from __future__ import generator_stop

import sys
from collections.abc import Sequence
from time import sleep
from typing import Any, Dict, List, Optional
from typing import Sequence as SequenceT
from typing import Set, TextIO, Tuple

from aria2p import Client
from aria2p.client import DEFAULT_HOST, DEFAULT_PORT, ClientException
from requests.exceptions import ConnectionError

from .dict import update
from .exceptions import DownloadFailed, ExternalProcedureUnavailable, InconsistentState, WouldBlockForever, assert_type


def aria_bool(value: Optional[bool]) -> Optional[str]:

    """aria2 rpc requires strings for some boolean arguments like 'continue'"""

    if value is None:
        return None
    elif value is True:
        return "true"
    elif value is False:
        return "false"
    else:
        raise ValueError(str(value))


class AriaDownloader:

    default_global_options = {
        "max-concurrent-downloads": 5,
        "remote-time": True,
    }

    default_options = {
        "max-connection-per-server": 1,
        "split": 5,
        "always-resume": True,
    }

    max_num_results = 100

    """ Download manager which uses aria2 instance to actually download the files.
        Tries to respect other users of the same instance and doesn't interfere with them.
    """

    def __init__(  # nosec
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        secret: str = "",
        poll: float = 1.0,
        global_options: Optional[dict] = None,
    ) -> None:

        """Initialize the aria2 client with `host`, `port` and `secret`.
        Poll aria2 every `poll` seconds.
        """

        self.aria2 = Client(host, port, secret)
        self.poll = poll

        if global_options:
            global_options = self.default_global_options.copy()
            global_options.update(global_options)
            self.aria2.change_global_option(global_options)
        else:
            self.aria2.change_global_option(self.default_global_options)

        self.gids: Set[str] = set()

    def query(self, method: str, *args: Any, **kwargs: Any) -> Any:

        try:
            return getattr(self.aria2, method)(*args, **kwargs)
        except ClientException as e:
            if e.code == 1:
                # either our code is bad, or some external actor removed our gid from aria
                raise InconsistentState(e.message)
            else:
                raise
        except ConnectionError as e:
            raise ExternalProcedureUnavailable(e)

    def pause_all(self) -> None:

        for gid in self.gids:
            self.query("pause", gid)

    def resume_all(self) -> None:

        for gid in self.gids:
            self.query("unpause", gid)

    def _entries(self, entries: Dict[str, Any]) -> Dict[str, Any]:
        return {entry["gid"]: entry for entry in entries if entry["gid"] in self.gids}

    def managed_downloads(self) -> int:

        return len(self.gids)

    def block_one(self, progress_file: Optional[TextIO] = sys.stdout) -> Tuple[str, str]:

        """Blocks until one download is done."""

        while True:
            """fixme: This loop has a (not very serious) race condition.

            For example a download might change its status from waiting to active
            during the two queries. Then it would not be found.
            This cannot be fixed by changing the query order as the status change graph
            (waiting<->active->stopped) cannot be sorted topologically.
            And even if you could, returning stopped downloads has priority over
            waiting/active ones, as otherwise we would block for too long.

            Does using a multi/batch-call fix this?
            """

            entries = self._entries(self.query("tell_stopped", 0, self.max_num_results))  # complete or error
            if entries:
                gid, entry = entries.popitem()

                try:
                    if entry["status"] == "complete":
                        assert len(entry["files"]) == 1
                        return gid, entry["files"][0]["path"]
                    elif entry["status"] == "error":
                        raise DownloadFailed(gid, entry["errorCode"], entry["errorMessage"])
                    else:
                        raise RuntimeError("Unexpected status: {}".format(entry["status"]))

                finally:
                    self.remove_stopped(gid)

            entries = self._entries(self.query("tell_active"))  # active
            if entries:
                if progress_file:
                    completed = sum(int(entry["completedLength"]) for entry in entries.values())
                    total = sum(int(entry["totalLength"]) for entry in entries.values())
                    speed = sum(int(entry["downloadSpeed"]) for entry in entries.values())
                    print(
                        f"{len(entries)} downloads: {completed}/{total} bytes {speed} bytes/sec",
                        file=progress_file,
                        end="\r",
                    )

                sleep(self.poll)
                continue

            entries = self._entries(self.query("tell_waiting", 0, self.max_num_results))  # waiting or paused
            if entries:
                print(f"{len(entries)} downloads waiting or paused", end="\r")
                sleep(self.poll)
                continue

            if self.gids:
                """Actually only this check is sensitive to race condition, as the looping logic
                would care of retrying otherwise.
                However this is the only way to check for external modifications.
                """
                raise InconsistentState(
                    "Some downloads got lost. We either encoutered a race condition \
                    or some external actor removed the download"
                )

            raise WouldBlockForever("No downloads active or waiting")

    def block_all(self) -> List[Tuple[Any, Optional[str]]]:

        ret: List[Tuple[Any, Optional[str]]] = []

        while True:
            try:
                gid, path = self.block_one()
                ret.append((None, path))
            except WouldBlockForever:
                break
            except DownloadFailed as e:
                ret.append((e.args, None))

        return ret

    def remove_stopped(self, gid: str) -> None:

        self.gids.remove(gid)

        # removes a complete/error/removed download
        # fails on active/waiting/paused (on CTRL-C for example)
        self.query("remove_download_result", gid)

    def block_gid(self, gid: str, progress_file: Optional[TextIO] = sys.stdout) -> str:

        """Blocks until download is done.
        If progress printing is not needed, `progress_file` should be set to `None`.
        Returns the path of the downloaded file on disk.
        """

        if gid not in self.gids:
            raise KeyError("Invalid GID")

        try:
            while True:
                s = self.query("tell_status", gid)

                status = s["status"]

                if status == "active":
                    if progress_file:
                        print(
                            s["completedLength"],
                            "/",
                            s["totalLength"],
                            "bytes",
                            s["downloadSpeed"],
                            "bytes/sec",
                            file=progress_file,
                            end="\r",
                        )

                elif status == "waiting":
                    if progress_file:
                        print("waiting", file=progress_file, end="\r")

                elif status == "paused":
                    if progress_file:
                        print("paused", file=progress_file, end="\r")

                elif status == "error":
                    raise DownloadFailed(
                        gid, s["errorCode"], s["errorMessage"]
                    )  # RuntimeError: No URI available. errorCode=8 handle

                elif status == "complete":
                    assert len(s["files"]) == 1
                    return s["files"][0]["path"]

                elif status == "removed":
                    raise RuntimeError("Someone removed our download...")

                else:
                    raise RuntimeError(f"Unexpected status: {status}")

                sleep(self.poll)
        finally:
            self.remove_stopped(gid)

    def download(
        self,
        uri: str,
        path: Optional[str] = None,
        filename: Optional[str] = None,
        headers: Optional[SequenceT[str]] = None,
        max_connections: Optional[int] = None,
        split: Optional[int] = None,
        continue_: Optional[bool] = None,
        retry_wait: Optional[int] = None,
        max_tries: Optional[int] = None,
        connect_timeout: Optional[int] = None,
        timeout: Optional[int] = None,
        no_netrc: Optional[bool] = None,
    ) -> str:

        """Downloads `uri` to directory `path`.
        Does not block. Returns a download identifier.
        """

        if headers is not None:
            assert_type("headers", headers, Sequence)

        options = self.default_options.copy()
        update(
            options,
            {
                "dir": path,
                "out": filename,
                "header": headers,
                "max-connection-per-server": max_connections,
                "split": split,
                "continue": aria_bool(continue_),
                "retry-wait": retry_wait,
                "max-tries": max_tries,
                "connect-timeout": connect_timeout,
                "timeout": timeout,
                "no-netrc": aria_bool(no_netrc),
            },
        )

        gid = self.query("add_uri", [uri], options)
        self.gids.add(gid)
        return gid

    def download_x(
        self,
        num: int,
        uri: str,
        path: Optional[str] = None,
        filename: Optional[str] = None,
        headers: Optional[SequenceT[str]] = None,
        max_connections: Optional[int] = None,
        split: Optional[int] = None,
        continue_: Optional[bool] = None,
        retry_wait: Optional[int] = None,
        max_tries: Optional[int] = None,
        connect_timeout: Optional[int] = None,
        timeout: Optional[int] = None,
        no_netrc: Optional[bool] = None,
    ) -> Optional[Tuple[str, str, str]]:

        queued_gid = self.download(
            uri,
            path,
            filename,
            headers,
            max_connections,
            split,
            continue_,
            retry_wait,
            max_tries,
            connect_timeout,
            timeout,
            no_netrc,
        )
        if self.managed_downloads() >= num:
            finished_gid, path = self.block_one()
            return queued_gid, finished_gid, path

        return None


class DownloadManager:

    """To use from a single thread.

    State transitions:
    waiting -> running (automatically)
    running -> paused (manually)
    paused -> running (manually)
    running -> complete (automatically)
    running -> error (automatically)
    """

    def __init__(self):
        pass

    def download_with_callback(self, url, path=None, filename=None, headers=None, force=False, func=None):
        """Starts or enqueues download and a unique id for that download job.
        if `force` is True, the download is started without regard for the current number
        of downloads and queue position.
        """

    def block_uid(self, uid):
        """Blocks until `uid` completes or errors
        and returns information about that download.
        """

    def block_one(self):
        """Block until any download completes or errors
        and returns information about that download.
        """

    def block_active(self, x):
        """Block if more than `x` downloads are currently active
        until x or less are active. Yields information about completed/errored downloads
        as they become available.
        """

    def cancel(self, uid, states=None):
        """Cancels a download identified by `uid`. if `states` is None, it will be
        - removed from the queue if waiting
        - canceled if downloading
        - removed if completed
        - removed if errored.
        The previous state will be returned,
        """

        # sets the status if `uid` to canceled.

    def clean(self, uid, states=None):
        """Removed all files associated to `uid` from disk. `states` is a list of acceptable states.
        For example ("stopped", "error") will only remove files if the download
        was stopped mid-progress or because of an error.
        Take notice that ("complete") will remove files of completed downloads from disk.
        """

        # doesn't change status

    def forget(self, uid):
        """Remove `uid` from the manager completely. It can only do so for downloads
        with the state "canceled".
        """

    # for convenience only

    def block_all(self, uid):
        return self.block_active(0)

    def download_and_block(self, url):
        uid = self.download_with_callback(url)
        return self.block_uid(uid)


if __name__ == "__main__":

    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument("uris", metavar="URI", nargs="+", help="URLs to download")
    parser.add_argument("--outpath", default=".", help="Output directory")
    parser.add_argument("--max", default=2, type=int, help="Maximum concurrent downloads")
    args = parser.parse_args()

    d = AriaDownloader()
    for uri in args.uris:
        path = d.download_x(args.max, uri, args.path)
        print(f"Downloaded {uri} to {path}")

    for a in d.block_all():
        print(a)
