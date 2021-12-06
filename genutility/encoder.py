from __future__ import generator_stop

from typing import Callable, Dict, Generic, Hashable, Iterable, Iterator, List, TypeVar, Union

import numpy as np
from nltk.tokenize import word_tokenize

from .func import identity

T = TypeVar("T")


class GenericLabelEncoder:

    """Encodes all hashable objects to integers"""

    def __init__(self):
        # type: () -> None

        self.reset()

    def reset(self):
        # type: () -> None

        self.object2idx = {}  # type: Dict[Hashable, int]
        self.idx2object = []  # type: List[Hashable]

    def encode(self, obj):
        # type: (Hashable, ) -> int

        """Encode a hashable `obj` to an integer."""

        size = len(self.idx2object)
        idx = self.object2idx.setdefault(obj, size)
        if idx == size:  # inserted new object
            self.idx2object.append(obj)

        return idx

    def encode_batch(self, objs):
        # type: (Iterable[Hashable], ) -> Iterator[int]

        for obj in objs:
            yield self.encode(obj)

    def decode(self, idx):
        # type: (int, ) -> Hashable

        """Decode an integer `idx` to the previously encoded object.
        Raises IndexError if the index is out of range.
        """

        return self.idx2object[idx]

    def decode_batch(self, indices):
        # type: (Iterable[int], ) -> Iterator[Hashable]

        for idx in indices:
            yield self.decode(idx)

    def __len__(self):
        # type: () -> int

        assert len(self.object2idx) == len(self.idx2object)
        return len(self.idx2object)


class BatchLabelEncoder(Generic[T]):

    """Similar to `sklearn.preprocessing.LabelEncoder` but accepts a list of sentences as inputs
    and returns a list of lists of integer labels.
    Warning: Calling `fit` doesn't reset the encoder. To do so call `reset()` explicitly.
    cf. `keras_preprocessing.text.Tokenizer`
    """

    def __init__(self, tokenizer: str) -> None:

        self.tokenizer: Callable[[str], Iterator[T]] = {
            "none": identity,
            "nltk": word_tokenize,
        }[tokenizer]
        self.reset()

    def reset(self):
        # type: () -> None

        """Initializes all mappings with empty containers."""

        self.token2idx = {}  # type: Dict[T, int]

        self.idx2count = []  # type: Union[List[int], np.ndarray]
        self.idx2token = []  # type: Union[List[T], np.ndarray]

    def finalize(self, vocab_size):
        # type: (int, ) -> None

        """This only keeps the most frequent `vocab_size` words in the vocabulary.
        This will change the assigned indices, so if `transform` was used before `finalize`,
        they cannot be transformed back using `inverse_transform`.
        """

        self.idx2count = np.array(self.idx2count)
        self.idx2token = np.array(self.idx2token)
        indices = np.argsort(-self.idx2count)[:vocab_size]

        self.idx2count = self.idx2count[indices]
        self.idx2token = self.idx2token[indices]

        self.token2idx = {token: i for i, token in enumerate(self.idx2token)}

    def partial_fit_single(self, token):
        # type: (T, ) -> int

        vocab_size = self.num_labels
        idx = self.token2idx.setdefault(token, vocab_size)
        if idx == vocab_size:  # inserted new token
            self.idx2count.append(1)
            self.idx2token.append(token)
        else:
            self.idx2count[idx] += 1

        return idx

    def partial_fit(self, sentence):
        # type: (str, ) -> None

        for token in self.tokenizer(sentence):
            self.partial_fit_single(token)

    def partial_fit_batch(self, sentences):
        # type: (Iterable[str], ) -> None

        for sentence in sentences:
            self.partial_fit(sentence)

    def fit_single(self, token):
        # type: (T, ) -> None

        self.partial_fit_single(token)

    def fit(self, sentence):
        # type: (str, ) -> None

        self.partial_fit(sentence)

    def fit_batch(self, sentences):
        # type: (Iterable[str], ) -> None

        self.partial_fit_batch(sentences)

    def transform_single(self, token):
        # type: (T, ) -> int

        """Unknown labels are skipped."""

        return self.token2idx[token]

    def transform(self, sentence, ignore=True):
        # type: (str, bool) -> Iterator[int]

        for token in self.tokenizer(sentence):
            try:
                yield self.transform_single(token)
            except KeyError:
                if ignore:
                    pass
                else:
                    raise

    def transform_batch(self, sentences, ignore=True):
        # type: (Iterable[str], bool) -> Iterator[List[int]]

        """Unknown labels are skipped."""

        for sentence in sentences:
            yield list(self.transform(sentence, ignore))

    def fit_transform_single(self, token):
        # type: (T, ) -> int

        return self.partial_fit_single(token)

    def fit_transform(self, sentences):
        # type: (str, ) -> Iterator[int]

        self.partial_fit(sentences)
        return self.transform(sentences)

    def fit_transform_batch(self, sentences):
        # type: (Iterable[str], ) -> Iterator[List[int]]

        self.partial_fit_batch(sentences)
        return self.transform_batch(sentences)

    def inverse_transform_single(self, idx):
        # type: (int, ) -> T

        return self.idx2token[idx]

    def inverse_transform(self, indices):
        # type: (Iterable[int], ) -> Iterator[T]

        for idx in indices:
            yield self.inverse_transform_single(idx)

    def inverse_transform_batch(self, list_of_indices):
        # type: (Iterable[Iterable[int]], ) -> Iterator[List[T]]

        for indices in list_of_indices:
            yield list(self.inverse_transform(indices))

    @property
    def num_labels(self):
        # type: () -> int

        assert len(self.token2idx) == len(self.idx2count) == len(self.idx2token)
        return len(self.idx2token)
