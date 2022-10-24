from __future__ import generator_stop

import csv
from typing import Dict, Iterator


def parse_imdb_csv(path: str) -> Iterator[Dict[str, str]]:

    with open(path, encoding="iso-8859-1", errors="strict", newline="") as fr:
        csvreader = csv.DictReader(fr)
        yield from csvreader
