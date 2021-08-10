from __future__ import generator_stop

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
	import bs4

def find_one(node, *args, **kwargs):
	# type: (bs4.element.Tag, *Any, **Any) -> bs4.element.Tag

	nodes = node.find_all(*args, **kwargs)

	if len(nodes) != 1:
		raise ValueError(f"Found {len(nodes)} nodes for: {args} {kwargs}")

	return nodes[0]
