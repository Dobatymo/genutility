from typing import Callable, Iterable, List, Optional

import numpy as np

Tokenizer = Callable[[str], Iterable[str]]


def hamming_distance(a: bytes, b: bytes) -> int:
    a = np.unpackbits(np.frombuffer(a, dtype=np.uint8))
    b = np.unpackbits(np.frombuffer(b, dtype=np.uint8))
    return np.count_nonzero(a != b)


def default_tokenizer(text: str) -> List[str]:
    return text.lower().split()


def same_words_similarity(a: str, b: str, tokenizer: Optional[Tokenizer] = None) -> int:
    tokenizer = tokenizer or default_tokenizer

    set_a = set(tokenizer(a))
    set_b = set(tokenizer(b))

    return len(set_a & set_b)
