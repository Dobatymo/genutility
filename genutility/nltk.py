from os import PathLike

from nltk.tokenize import word_tokenize


def count_words_in_file(path: PathLike, encoding: str = "utf-8") -> int:
    with open(path, encoding=encoding) as fr:
        return sum(len(word_tokenize(line)) for line in fr)
