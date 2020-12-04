import dbm
import gzip
import pickle  # nosec
from typing import TYPE_CHECKING

from .dbm import dbm_items

if TYPE_CHECKING:
	from collections.abc import MutableMapping
	from typing import Any, Callable, ContextManager, Iterator, Tuple

def read_dbm_httpcache(path, open_func=dbm.open):
	# type: (str, Callable[[str], ContextManager[MutableMapping]]) -> Iterator[Tuple[bytes, float, Any]]

	""" Loads scrapy dbm http cache files.
		Uses pickle so only use on trusted file.
	"""

	with open_func(path, "r") as db:

		for key, value in dbm_items(db):

			if key.endswith(b"_data"):
				hash = key[:-5]
				time = float(db[hash + b"_time"])
				data = pickle.loads(value)  # nosec

				if data["headers"].get(b"Content-Encoding", []) == [b"gzip"]:
					data["body"] = gzip.decompress(data["body"])
					data["headers"][b"Content-Encoding"] = []

				yield hash, time, data

if __name__ == "__main__":

	from argparse import ArgumentParser

	parser = ArgumentParser()
	parser.add_argument("path", help="path to db file")
	args = parser.parse_args()

	for hash, time, data in read_dbm_httpcache(args.path):
		print(data["url"][-50:], len(data["body"]), data["body"][:30])
