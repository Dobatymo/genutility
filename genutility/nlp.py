from __future__ import generator_stop

from itertools import islice
from string import ascii_letters
from typing import Dict, Iterable, Iterator, List, Optional, Sequence, TextIO, Union

from nltk.tokenize import word_tokenize as tokenize
from nltk.tokenize.treebank import TreebankWordDetokenizer

from .file import PathOrTextIO
from .gensim import KeyedVectors

english_word_chars = set(ascii_letters) | {"-", "'"}


def resembles_english_word(word: str) -> bool:

    """Returns True if `word` only consists of English letters and - or '."""

    return all(t in english_word_chars for t in word)


def gensim_indexer(embeddings: KeyedVectors, doc: str, ignore: bool = True) -> Iterator[int]:

    for word in tokenize(doc):
        try:
            yield embeddings.vocab[word.lower()].index
        except KeyError:
            if ignore:
                pass
            else:
                raise


def batch_gensim_indexer(embeddings: KeyedVectors, docs: Iterable[str], ignore: bool = True) -> Iterator[List[int]]:

    for doc in docs:
        yield list(gensim_indexer(embeddings, doc, ignore))


def load_freqs(fname: Union[str, TextIO], normalize: bool = False, limit: Optional[int] = None) -> Dict[str, int]:

    with PathOrTextIO(fname, "rt", encoding="utf-8") as fin:
        freqs = dict()

        for line in islice(fin, limit):
            word, count = line.split()
            freqs[word] = int(count)

    if normalize:
        total = sum(freqs.keys())

        for word, count in freqs.items():
            freqs[word] = count / total

    return freqs


def detokenize(tokens: Sequence[str]) -> str:

    """Simply wraps the nltk `TreebankWordDetokenizer` into a convenience function."""

    detokenizer = (
        TreebankWordDetokenizer()
    )  # doesn't use custom `__init__` so should be fast enough to instantiate every time
    s = detokenizer.detokenize(tokens)
    return s
