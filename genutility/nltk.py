from __future__ import generator_stop

from typing import TYPE_CHECKING

from nltk.tokenize import word_tokenize

if TYPE_CHECKING:
    from os import PathLike


def count_words_in_file(path, encoding="utf-8"):
    # type: (PathLike, str) -> int

    with open(path, encoding=encoding) as fr:
        return sum(len(word_tokenize(line)) for line in fr)
