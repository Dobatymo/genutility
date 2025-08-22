from typing import Optional, Tuple, Union

import numpy as np
from sklearn.model_selection import StratifiedShuffleSplit


def train_test_split_indices(
    y: np.ndarray,
    test_size: Optional[Union[int, float]] = None,
    train_size: Optional[Union[int, float]] = None,
    random_state: Optional[int] = None,
) -> Tuple[np.ndarray, np.ndarray]:
    sss = StratifiedShuffleSplit(test_size=test_size, train_size=train_size, random_state=random_state)
    X = np.zeros(len(y))

    train, test = next(sss.split(X, y))
    return train, test
