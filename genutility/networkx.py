from __future__ import generator_stop

from itertools import chain
from typing import TYPE_CHECKING

from networkx import Graph, connected_components

if TYPE_CHECKING:
    from typing import Sequence, TypeVar

    import numpy as np

    T = TypeVar("T")


def complete_weighted_bipartite_graph(first, second, weights):
    # type: (Sequence[T], Sequence[T], np.ndarray) -> Graph

    graph = Graph()

    graph.add_nodes_from(first, bipartite=0)
    graph.add_nodes_from(second, bipartite=1)

    for i in range(len(first)):
        for j in range(len(second)):
            graph.add_edge(first[i], second[j], weight=weights[i][j])

    return graph


def connected_subgraph(graph, minsize=2):
    # type: (Graph, int) -> Graph

    """Returns all the connected subgraphs of `graph`,
    which are at least of size `minsize`.
    """

    nodelist = list(chain.from_iterable(comp for comp in connected_components(graph) if len(comp) >= minsize))
    return graph.subgraph(nodelist)
