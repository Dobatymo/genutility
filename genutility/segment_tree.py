from typing import Callable, List, Optional


class SegmentTree:
    # ported from https://codeforces.com/blog/entry/18051

    t: List[Optional[int]]

    def __init__(self, arr: List[int], func: Callable[[int, int], int], initializer: int) -> None:
        self.n = len(arr)
        self.func = func
        self.initializer = initializer

        self.t = [None] * self.n + arr  # type

    def build(self) -> None:
        i = self.n - 1
        while i > 0:
            self.t[i] = self.func(self.t[i << 1], self.t[i << 1 | 1])
            i -= 1

    def modify(self, p: int, value: int) -> None:
        p += self.n
        self.t[p] = value

        while p > 1:
            val = self.func(self.t[p], self.t[p ^ 1])
            p >>= 1
            self.t[p] = val

    def query(self, left: int, right: int) -> int:
        if left >= right or not 0 <= left <= self.n or not 0 <= right <= self.n:
            raise ValueError(f"Interval [{left}, {right}) out of range")

        res = self.initializer
        left += self.n
        right += self.n

        while left < right:
            if left & 1:
                res = self.func(res, self.t[left])
                left += 1
            if right & 1:
                right -= 1
                res = self.func(res, self.t[right])

            left >>= 1
            right >>= 1

        return res
