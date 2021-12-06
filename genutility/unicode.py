from __future__ import generator_stop

from collections import defaultdict
from pathlib import Path
from sys import maxunicode
from tempfile import gettempdir
from unicodedata import category

from .pickle import cache  # nosec


@cache(Path(gettempdir() + "/unicode_categories.{ppv}.pkl"), ignoreargs=True)
def unicode_categories():
    unicode_categories = defaultdict(set)
    for c in map(chr, range(maxunicode + 1)):
        unicode_categories[category(c)].add(c)
    return unicode_categories
