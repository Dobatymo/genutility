from __future__ import generator_stop

from typing import TYPE_CHECKING

import toml

if TYPE_CHECKING:
    from typing import Any


def read_toml(path):
    # type: (str, ) -> Any

    with open(path, encoding="utf-8") as fr:
        return toml.load(fr)


def write_toml(obj, path):
    # type: (Any, str) -> None

    with open(path, "w", encoding="utf-8") as fw:
        toml.dump(obj, fw)
