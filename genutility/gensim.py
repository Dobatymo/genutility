from __future__ import generator_stop

from collections import namedtuple
from itertools import islice
from typing import Any, Callable, Collection, Iterable, Iterator, Optional, TextIO, Tuple, Union

import numpy as np
from gensim.models.keyedvectors import KeyedVectors as KeyedVectorsOriginal

from .file import PathOrTextIO

Vocab = namedtuple("Vocab", ["index", "count"])


class DuplicateEntry(ValueError):
    pass


def false(x: Any) -> bool:

    return False


class KeyedVectors(KeyedVectorsOriginal):

    """Enhancement of the original `gensim` `KeyedVectors` class. Supports loading of `glove` and
    `muse` word vector files.
    """

    @classmethod
    def load_a_format(
        cls,
        fin: Iterable[str],
        vocab_size: int,
        vector_size: int,
        datatype: Any = np.float32,
        discard: Optional[Callable[[str], bool]] = None,
    ) -> KeyedVectorsOriginal:

        discard = discard or false

        result = cls(vector_size)
        result.vector_size = vector_size
        result.vectors = np.zeros((vocab_size, vector_size), dtype=datatype)
        result.expandos["count"] = np.zeros(vocab_size, dtype=np.int64)

        for line in fin:
            word, vect = line.rstrip().split(" ", 1)

            if discard(word):
                continue

            weights = np.fromstring(vect, sep=" ", dtype=np.float32)
            # raise ValueError("invalid vector on line %s; is vector_size incorrect or file otherwise damaged?" % (i+1,))

            if word in result.key_to_index:
                raise DuplicateEntry(word)

            word_id = len(result.index_to_key)
            result.key_to_index[word] = word_id
            result.expandos["count"][word_id] = vocab_size - word_id
            result.vectors[word_id] = weights
            result.index_to_key.append(word)

        real_size = len(result.index_to_key)

        if real_size != vocab_size:
            if discard is None:
                raise EOFError("unexpected end of input; is vocab_size incorrect or file otherwise damaged?")
            else:
                result.vectors.resize((real_size, vector_size))  # this should be no-copy
                result.expandos["count"].resize(real_size)  # this should be no-copy

        return result

    def add(self, wwc: Collection[Tuple[str, np.ndarray, int]]) -> Iterator[Vocab]:

        """`wwc` is a collection of (word, weights, count) tuples"""

        vocab_size, vector_size = self.vectors.shape
        self.vectors.resize((vocab_size + len(wwc), vector_size))
        self.expandos["count"].resize(vocab_size + len(wwc))

        for i, (word, weights, count) in enumerate(wwc):
            word_id = vocab_size + i
            self.key_to_index[word] = word_id
            self.expandos["count"][word_id] = count
            self.vectors[word_id] = weights
            self.index_to_key.append(word)
            yield Vocab(word_id, count)

    def add_word(self, word: str, weights: Optional[np.ndarray] = None, count: int = 1):
        if weights is None:
            vocab_size, vector_size = self.vectors.shape
            weights = np.random.randn(1, vector_size)

        return list(self.add([(word, weights, count)]))[0]

    @classmethod
    def load_muse_format(
        cls, fname: Union[str, TextIO], limit: Optional[int] = None, discard: Optional[Callable[[str], bool]] = None
    ) -> KeyedVectorsOriginal:

        """reads at most `limit` vectors from muse file, if `discard` is not None it might be less.
        discard is a callable which should return False if word should not be loaded from file.
        """

        with PathOrTextIO(fname, "rt", encoding="utf-8", newline="\n") as fin:
            vocab_size_, vector_size = map(int, next(fin).split(" "))
            if limit is None:
                vs = vocab_size_
            else:
                vs = min(vocab_size_, limit)

            try:
                return cls.load_a_format(islice(fin, limit), vs, vector_size, discard=discard)
            except DuplicateEntry as e:
                raise ValueError(f"duplicate word '{e}' in {fname}")

    @classmethod
    def load_glove_format(
        cls, fname: Union[str, TextIO], limit: int, vector_size: int, discard: Optional[Callable[[str], bool]] = None
    ) -> KeyedVectorsOriginal:

        """Reads at most `limit` vectors from glove file, if `discard` is not None it might be less.
        `discard` is a callable which should return False if word should not be loaded from file.
        """

        with PathOrTextIO(fname, "rt", encoding="utf-8") as fin:
            try:
                return cls.load_a_format(islice(fin, limit), limit, vector_size, discard=discard)
            except DuplicateEntry as e:
                raise ValueError(f"duplicate word '{e}' in {fname}")

    def get_keras_embedding(self, train_embeddings: bool = False, mask_zero: bool = True) -> "Embedding":  # noqa: F821

        try:
            from keras.layers import Embedding
        except ImportError:
            raise ImportError("Please install Keras to use this function")

        if mask_zero:
            self.index_to_key = [None] + self.index_to_key
            zero_vec = np.zeros((1, self.vector_size))
            self.vectors = np.concatenate([zero_vec, self.vectors], axis=0)

        weights = self.vectors

        # set `trainable` as `False` to use the pretrained word embedding
        # No extra mem usage here as `Embedding` layer doesn't create any new matrix for weights
        layer = Embedding(
            input_dim=weights.shape[0],
            output_dim=weights.shape[1],
            weights=[weights],
            trainable=train_embeddings,
            mask_zero=mask_zero,
        )
        return layer

    def transform_words_to_indices(self, words: Collection[str]) -> Iterator[int]:

        return (self.key_to_index[word] for word in words)

    def transform_words_to_indices_tuple(self, words: Collection[str]) -> Tuple[int, ...]:

        return tuple(self.transform_words_to_indices(words))


if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--glove-file")
    parser.add_argument("--muse-file")
    parser.add_argument("--dimensions", type=int, default=300)
    args = parser.parse_args()

    if args.glove_file:
        word_vectors = KeyedVectors.load_glove_format(args.glove_file, 400000, args.dimensions)
        print(word_vectors.most_similar(positive=["woman", "king"], negative=["man"]))

    if args.muse_file:
        word_vectors = KeyedVectors.load_muse_format(args.muse_file)
        print(word_vectors.most_similar(positive=["woman", "king"], negative=["man"]))
