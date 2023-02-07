from typing import Any

import toml


def read_toml(path: str) -> Any:
    with open(path, encoding="utf-8") as fr:
        return toml.load(fr)


def write_toml(obj: Any, path: str) -> None:
    with open(path, "w", encoding="utf-8") as fw:
        toml.dump(obj, fw)
