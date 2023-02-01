from collections import defaultdict
from typing import Callable, DefaultDict, Dict, Generic, Hashable, ItemsView, Iterable, Optional, Tuple, TypeVar

H1 = TypeVar("H1", bound=Hashable)
H2 = TypeVar("H2", bound=Hashable)


class MultiCounter(Generic[H1, H2]):
    def __init__(self, transform: Optional[Callable[[H2], H2]] = None):
        self.counts: DefaultDict[H1, Dict[H2, int]] = defaultdict(dict)
        self.transform = transform

        if transform:
            self.add = self._add_transform
            self.update = self._update_transform
        else:
            self.add = self._add
            self.update = self._update

    def _add(self, name: H1, item: H2) -> None:
        self.counts[name][item] = self.counts[name].get(item, 0)

    def _add_transform(self, name: H1, item: H2) -> None:
        item = self.transform(item)
        self.counts[name][item] = self.counts[name].get(item, 0)

    def _update(self, it: Iterable[Tuple[H1, H2]]) -> None:
        _counts = self.counts
        for name, item in it:
            _counts[name][item] = _counts[name].get(item, 0)

    def _update_transform(self, it: Iterable[Tuple[H1, H2]]) -> None:
        _counts = self.counts
        func = self.transform
        for name, item in it:
            item = func(item)
            _counts[name][item] = _counts[name].get(item, 0)

    def items(self) -> ItemsView[H1, Dict[H2, int]]:
        return self.counts.items()

    def update(self, it: Iterable[Tuple[H1, H2]]):
        raise NotImplementedError

    def add(self, name: H1, item: H2):
        raise NotImplementedError
