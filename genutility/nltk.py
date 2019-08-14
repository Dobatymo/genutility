from __future__ import absolute_import, division, print_function, unicode_literals

from io import open

from nltk.tokenize import word_tokenize

def count_words_in_file(path, encoding="utf-8"):
	# type: (Path, ) -> int

	with open(path, "r", encoding=encoding) as fr:
		return sum(len(word_tokenize(line)) for line in fr)
