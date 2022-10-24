from __future__ import generator_stop

import os.path
from configparser import ConfigParser
from importlib.util import find_spec
from typing import Any, Dict, Optional, Union

from .os import get_appdata_dir


def sort_config(inpath: str, outpath: str) -> None:

    from sortedcontainers import SortedDict

    config = ConfigParser(dict_type=SortedDict)
    config.read(inpath, encoding="utf-8")
    with open(outpath, "w", encoding="utf-8") as fw:
        config.write(fw)


def _load(*names: str) -> Dict[str, Any]:

    from .toml import read_toml

    name = names[-1]
    configfilename = name + ".toml"

    # try appdata directory
    try:
        appdata_path = os.path.join(get_appdata_dir(), *names, configfilename)
        return read_toml(appdata_path)
    except FileNotFoundError:
        pass

    # try module directory
    try:
        spec = find_spec(name)

        if spec is None:
            raise ImportError(f"No module named '{name}'")  # or FileNotFoundError?

        if spec.has_location:
            assert spec.origin  # for mypy
            modpath = os.path.dirname(spec.origin)
        else:
            try:
                modpath = spec.submodule_search_locations[0]  # type: ignore
            except (TypeError, IndexError):
                raise FileNotFoundError

        return read_toml(os.path.join(modpath, configfilename))
    except (ImportError, FileNotFoundError):
        pass

    # try working directory
    try:
        return read_toml(configfilename)
    except FileNotFoundError:
        raise FileNotFoundError(
            f"{configfilename} could not be found in application data, module path or current directory"
        )


def load(*names: str, json_schema: Optional[Union[dict, str]] = None) -> Dict[str, Any]:

    from .json import read_json_schema

    obj = _load(*names)

    if json_schema is None:
        return obj

    from jsonschema import validate

    if isinstance(json_schema, str):
        json_schema = read_json_schema(json_schema)

    validate(obj, json_schema)
    return obj
