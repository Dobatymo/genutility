from math import log
from typing import Callable, Hashable, Iterable, List, Optional, Union

from genutility.ops import logical_xnor
from genutility.sys import bitness


class HyperLogLog:
    """A HyperLogLog is a probabilistic data structure. It can approximately calculate the cardinality
    of a set and supports unions with other HLLs. It uses a constant amount of memory.
    """

    registers: List[int]

    def __init__(self, b: int = 14, hashfunc: Optional[Callable] = None, hashbits: Optional[int] = None) -> None:
        assert b >= 4 and logical_xnor(hashfunc, hashbits)

        self.b = b

        if hashfunc:
            self.hash = hashfunc
        else:
            self.hash = hash

        if hashbits:
            self.width = hashbits
        else:
            self.width = bitness()

        self.maxsize = 2**self.width

        self.m = 2**self.b

        if self.m == 16:
            self.alpha = 0.673
        elif self.m == 32:
            self.alpha = 0.697
        elif self.m == 64:
            self.alpha = 0.709
        else:
            self.alpha = 0.7213 / (1 + 1.079 / self.m)

        self.registers = [0] * self.m

    @property
    def error(self) -> float:
        return 1.04 / (self.m**0.5)

    def _merge_registers(self, other: "HyperLogLog") -> List[int]:
        if self.b != other.b or self.hash != other.hash or self.width != other.width:
            raise ValueError("HyperLogLog object need to have the same number of registers and same hashes")

        return list(map(max, self.registers, other.registers))  # type: ignore[arg-type]

    def add(self, value: Hashable) -> None:
        h = self.hash(value)

        # memory layout: zeros[hashbits-b], register[b].
        # register first and then zeros doesn't work as well in python,
        # because shifting to the left doesn't cut off
        register = (2**self.b - 1) & h  # same as h % self.b
        zeroes = self.width - self.b - (h >> self.b).bit_length()

        self.registers[register] = max(self.registers[register], zeroes)

    def update(self, other: Union["HyperLogLog", Iterable]) -> None:
        if isinstance(other, HyperLogLog):
            self.registers = self._merge_registers(other)
        else:
            for value in other:
                self.add(value)

    def __len__(self) -> int:
        DV_est = self.alpha * self.m**2 * 1 / sum(2 ** (-r) for r in self.registers)

        if DV_est < 5 / 2 * self.m:  # small range correction
            V = self.registers.count(0)
            if V == 0:  # no empty registers
                DV = DV_est
            else:
                DV = self.m * log(self.m / V)  # i.e. balls and bins correction

        elif DV_est <= self.maxsize / 30:
            DV = DV_est
        else:  # large range correction
            DV = -self.maxsize * log(1 - DV_est / self.maxsize)

        return int(DV)

    def clear(self) -> None:
        self.registers = [0] * self.m

    def union(self, other: "HyperLogLog") -> "HyperLogLog":
        registers = self._merge_registers(other)

        hll = HyperLogLog(self.b, self.hash, self.width)
        hll.registers = registers
        return hll

    def __or__(self, other: "HyperLogLog") -> "HyperLogLog":
        return self.union(other)

    def __ror__(self, other: "HyperLogLog") -> "HyperLogLog":
        self.registers = self._merge_registers(other)
        return self
