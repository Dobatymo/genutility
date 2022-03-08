from __future__ import generator_stop

import csv
from itertools import islice

import re2 as re

from .time import PrintStatementTime

# UNFINISHED!!! use re2 or hyperscan for pathological regex


class Browscap:
    def __init__(self, path="browscap.csv"):
        self.path = path

    @staticmethod
    def convert_to_regex(pattern):
        ret = f"^{re.escape(pattern)}$"  # fnmatch.translate(pattern)
        return ret.replace("\\?", ".").replace("\\*", ".*")

    def iter_patterns(self):
        with open(self.path, newline="") as fr:
            csvreader = csv.reader(fr)
            for row in islice(csvreader, 2, None):
                yield self.convert_to_regex(row[0]), row[6]

    def match_v1(self, useragent):
        data = list((re.compile(p, re.IGNORECASE), t) for p, t in self.iter_patterns())

        with PrintStatementTime():
            for pattern, type in data:
                if pattern.match(useragent):
                    print(type)

    def match_v2(self, useragent):
        pattern = "|".join(p for p, t in self.iter_patterns())
        pattern = re.compile(pattern, re.IGNORECASE, max_mem=1024**3)

        with PrintStatementTime():
            if pattern.match(useragent):
                print(True)


if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument("path", help="browscap.csv file")
    args = parser.parse_args()

    cap = Browscap(args.path)
    # cap.match_v1("Firefox")
    cap.match_v2("Firefox")
