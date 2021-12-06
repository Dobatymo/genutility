from __future__ import generator_stop


class RingList:

    """bad complexity, moves all data if ring is full"""

    def __init__(self, length):
        self.data = []
        self.full = False
        self.max = length
        self.cur = 0

    def append(self, x):
        if self.full:
            for i in range(self.cur - 1):
                self.data[i] = self.data[i + 1]
            self.data[self.cur - 1] = x
        else:
            self.data.append(x)
            self.cur += 1
            if self.cur == self.max:
                self.full = True

    def get(self):
        return self.data

    def remove(self):
        if self.cur > 0:
            del self.data[self.cur - 1]
            self.cur -= 1

    def size(self):
        return self.cur

    def maxsize(self):
        return self.max

    def __str__(self):
        return "".join(self.data)
