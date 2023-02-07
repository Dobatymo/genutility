import numpy as np


class LinearRegression:

    """Linear regression optimized by gradient descent."""

    def __init__(self, X: np.ndarray, y: np.ndarray, alpha: float = 0.01) -> None:
        """
        X: float[A, B]
        Y: float[A]
        """

        if len(X.shape) != 2:
            raise ValueError("X must be 2-dimensional")
        if len(y.shape) != 1:
            raise ValueError("y must be 1-dimensional")

        self.K = X.shape[1] + 1  # one extra dimension for the bias term
        self.M = len(y)
        self.y = y
        self.α = alpha

        row = np.ones((self.M, 1))
        self.X = np.concatenate([row, X], axis=-1)
        assert self.X.shape == (self.M, self.K)

        self.weights = np.random.random_sample(self.K)

    def predict(self, x: np.ndarray) -> float:
        """
        x: float[B]
        """

        return np.matmul(x, self.weights)

    def epoch(self) -> None:
        self.weights -= self.α * np.matmul(self.X.T, self.predict(self.X) - self.y)  # [K]

    def fit(self, n_iter: int = 100, verbose: bool = False) -> None:
        for i in range(n_iter):
            if verbose:
                print("SGD itertion:", i)
            self.epoch()

    def getParams(self: np.ndarray) -> float:
        """
        returns: float[B-1]
        """

        return self.weights[1:]

    def getIntercept(self) -> float:
        return self.weights[0]
