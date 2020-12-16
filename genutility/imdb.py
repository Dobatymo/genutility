from __future__ import generator_stop

import csv
from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from typing import Dict, Iterator

def parse_imdb_csv(path):
	# type: (str, ) -> Iterator[Dict[str, str]]

	with open(path, "r", encoding="iso-8859-1", errors="strict", newline="") as fr:
		csvreader = csv.DictReader(fr)
		for row in csvreader:
			yield row
