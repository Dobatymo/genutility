from __future__ import generator_stop

import dbm
import gzip
import logging
import pickle  # nosec
import warnings
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Callable, ContextManager, Iterator, Optional, Tuple

import scrapy

from .dbm import dbm_items
from .stdio import print_terminal_progress_line

if TYPE_CHECKING:
    from collections.abc import MutableMapping


def read_dbm_httpcache(path, open_func=dbm.open, decompress=True):
    # type: (str, Callable[[str, str], ContextManager[MutableMapping]], bool) -> Iterator[Tuple[bytes, float, Any]]

    """Loads scrapy dbm http cache files.
    Uses pickle so only use on trusted file.
    """

    if decompress:
        import brotli

    with open_func(path, "r") as db:

        for key, value in dbm_items(db):

            if key.endswith(b"_data"):
                hash = key[:-5]
                time = float(db[hash + b"_time"])
                data = pickle.loads(value)  # nosec

                if decompress:
                    ce = data["headers"].get(b"Content-Encoding", [])
                    if ce == [b"gzip"]:
                        data["body"] = gzip.decompress(data["body"])
                        data["headers"][b"Content-Encoding"] = []
                    elif ce == [b"br"]:
                        data["body"] = brotli.decompress(data["body"])
                        data["headers"][b"Content-Encoding"] = []
                    elif ce:
                        warnings.warn(f"Unsupported Content-Encoding: {ce}")

                yield hash, time, data


def print_progress(spider: scrapy.Spider) -> None:

    queue = len(spider.crawler.engine.slot.scheduler)
    requests = len(spider.crawler.engine.slot.scheduler.df.fingerprints)
    delta = datetime.utcnow() - spider.crawler.stats.get_value("start_time")
    items = spider.crawler.stats.get_value("item_scraped_count", 0)
    files = spider.crawler.stats.get_value("file_status_count/downloaded", 0)
    warnings = spider.crawler.stats.get_value("log_count/ERROR", 0)
    errors = spider.crawler.stats.get_value("log_count/WARNING", 0)
    cachehit = spider.crawler.stats.get_value("httpcache/hit", 0)
    cachemiss = spider.crawler.stats.get_value("httpcache/miss", 0)

    deltaseconds = timedelta(seconds=int(delta.total_seconds()))

    out = (
        f"{deltaseconds} requests: {requests:07d}, queue: {queue:07d}, items: {items:07d}, files: {files:07d}"
        f", warn/err: {warnings:05d}/{errors:05d}, cache: {cachehit:07d}/{cachehit+cachemiss:07d}"
    )
    print_terminal_progress_line(out)


def get_url_logger(urllogfile: Optional[str], name: str = "urllog", funcname: bool = False) -> logging.Logger:
    if urllogfile:
        handler = logging.FileHandler(urllogfile, encoding="utf-8", delay=True)
    else:
        handler = logging.NullHandler()

    urllog = logging.getLogger(name)
    urllog.propagate = False
    urllog.setLevel(logging.INFO)

    handler.setLevel(logging.INFO)
    if funcname:
        fmtstring = "%(asctime)s\t%(funcName)10s\t%(message)s"
    else:
        fmtstring = "%(asctime)s\t%(message)s"
    formatter = logging.Formatter(fmtstring)
    handler.setFormatter(formatter)
    urllog.addHandler(handler)
    return urllog


if __name__ == "__main__":

    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument("path", help="path to db file")
    args = parser.parse_args()

    for hash, time, data in read_dbm_httpcache(args.path):
        print(data["url"][-50:], len(data["body"]), data["body"][:30])
