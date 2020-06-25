from __future__ import absolute_import, division, print_function, unicode_literals

from builtins import map, chr, range

from unicodedata import category
from sys import maxunicode
from collections import defaultdict
from tempfile import gettempdir

from .pickle import cache  # nosec

@cache(gettempdir() + "/unicode_categories.{ppv}.pkl", ignoreargs=True)
def unicode_categories():
	unicode_categories = defaultdict(set)
	for c in map(chr, range(maxunicode + 1)):
		unicode_categories[category(c)].add(c)
	return unicode_categories
