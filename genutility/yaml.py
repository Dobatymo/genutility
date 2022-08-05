from __future__ import generator_stop

from typing import Any

from ruamel.yaml import YAML

from ._files import PathType


def read_yaml(path: PathType) -> Any:

    with open(path, encoding="utf-8") as fr:
        yaml = YAML(typ="safe")
        return yaml.load(fr)


def write_yaml(obj: PathType, path: Any) -> None:

    with open(path, "w", encoding="utf-8") as fw:
        yaml = YAML(typ="safe")
        yaml.dump(obj, fw)
