from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

class Vocab:

    count: int
    index: int
    def __init__(self, **kwargs: Any) -> None: ...
    def __lt__(self, other) -> bool: ...
    def __str__(self) -> str: ...

class KeyedVectors:
    def __init__(self, vector_size: int) -> None: ...
    def most_similar(
        self,
        positive: Optional[List[Union[str, int]]],
        negative: Optional[List[Union[str, int]]],
        topn: int = ...,
        clip_start: int = ...,
        clip_end: Optional[int] = ...,
        indexer: Optional[KeyedVectors] = ...,
    ) -> List[Tuple[Union[str, int], float]]: ...
    vectors: np.ndarray
    index2word: List[str]
    vector_size: int
    vocab: Dict[str, Vocab]
