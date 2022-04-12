from __future__ import generator_stop

from typing import Any

import bs4


def find_one(node: bs4.element.Tag, *args: Any, **kwargs: Any) -> bs4.element.Tag:

    nodes = node.find_all(*args, **kwargs)

    if len(nodes) != 1:
        raise ValueError(f"Found {len(nodes)} nodes for: {args} {kwargs}")

    return nodes[0]


def find_zero_or_one(node: bs4.element.Tag, *args: Any, **kwargs: Any) -> bs4.element.Tag:

    nodes = node.find_all(*args, **kwargs)

    if len(nodes) == 0:
        return None
    elif len(nodes) == 1:
        return nodes[0]
    else:
        raise ValueError(f"Found {len(nodes)} nodes for: {args} {kwargs}")
