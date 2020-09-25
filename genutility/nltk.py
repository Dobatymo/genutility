from __future__ import absolute_import, division, print_function, unicode_literals

from io import open

from nltk.tokenize import word_tokenize

from .compat.os import PathLike


def count_words_in_file(path, encoding="utf-8"):
	# type: (PathLike, ) -> int

	with open(path, "r", encoding=encoding) as fr:
		return sum(len(word_tokenize(line)) for line in fr)
