from __future__ import generator_stop

from collections import defaultdict
from typing import DefaultDict, Dict, Generic, Iterable, Optional, Set, Tuple, TypeVar, Union

T = TypeVar("T")
U = TypeVar("U")

_sentinel = object()


class CaseDict(Generic[T]):

    """Saves values for cased strings, but makes them retrievable using the lower cased version
    of the string as well.
    """

    def __init__(self):
        # type: () -> None

        self.d: Dict[str, T] = dict()
        self.casemap: DefaultDict[str, Set[str]] = defaultdict(set)

    def __len__(self) -> int:

        return len(self.d)

    def __setitem__(self, k: str, v: T) -> None:

        self.d[k] = v
        self.casemap[k.lower()].add(k)

    def keys(self) -> Iterable[str]:

        return self.d.keys()

    def ikeys(self) -> Iterable[str]:

        return self.casemap.keys()

    def values(self) -> Iterable[T]:

        return self.d.values()

    def items(self) -> Iterable[Tuple[str, T]]:

        return self.d.items()

    def __getitem__(self, k: str) -> T:

        return self.d[k]

    def igetitem(self, k: str) -> Dict[str, T]:

        results = self.casemap.get(k.lower())
        if results:
            return {k: self.d[k] for k in results}

        raise KeyError(k)

    def __contains__(self, k: str) -> bool:

        return k in self.d

    def icontains(self, k: str) -> bool:

        return k.lower() in self.casemap

    def __delitem__(self, k: str) -> None:

        del self.d[k]
        s = self.casemap[k.lower()]
        s.remove(k)
        if not s:
            del self.casemap[k.lower()]

    def idelitem(self, k: str) -> None:

        results = self.casemap.pop(k.lower())  # raise KeyError if it doesn't exist

        for r in results:
            del self.d[r]

    def get(self, k: str, default: Optional[T] = None) -> Optional[T]:

        return self.d.get(k, default)

    def iget(self, k: str, default: U = _sentinel) -> Union[Dict[str, T], U]:

        try:
            return self.igetitem(k)
        except KeyError:
            if default is _sentinel:
                return {}
            else:
                return default

    # new

    def igetitemset(self, k: str) -> Set[str]:

        return self.casemap[k.lower()]

    def igetset(self, k: str, default: U = _sentinel) -> Union[Set[str], U]:

        if default is _sentinel:
            default = set()
        return self.casemap.get(k.lower(), default)
