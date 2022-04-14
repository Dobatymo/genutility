from __future__ import generator_stop

import re
from typing import List

re_paragraphs = re.compile(r"((?:[^\n][\n]?)+)")


def split_paragraphs(text):
    # type: (str, ) -> List[str]

    return re_paragraphs.findall(text)
