"""graph_generator.py - builds the weighted interference graph.

An edge between two nodes represents potential radio interference if both
nodes are assigned the same channel. Edge weights quantify the severity
of the clash, scaled by operational node priorities if configured.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Union

import networkx as nx

import config
from scenario import Scenario


def build_interference_graph(
    scenario: Optional[Union[Scenario, str]] = None,
    nodes: Optional[List[str]] = None,
    edges: Optional[List[Tuple[str, str, float]]] = None,
    node_roles: Optional[Dict[str, str]] = None,
    node_priorities: Optional[Dict[str, float]] = None,
    priority_mode: str = "product",
) -> nx.Graph:
    """Return an undirected weighted networkx Graph.

    Can be constructed from:
      1. A Scenario object or path to a JSON scenario file.
      2. Explicit nodes and edges lists.
      3. Defaults from config.py if no arguments are provided.

    Node attributes:
        'role': Functional role in the emergency mesh.
        'priority': Operational priority multiplier (>= 1.0).

    Edge attributes:
        'weight': Raw synthetic interference weight.
        'effective_weight': Priority-weighted penalty paid if both ends share a channel.
    """
    if scenario is not None:
        if isinstance(scenario, str):
            sc = Scenario.from_json(scenario)
        else:
            sc = scenario
        nodes = sc.nodes
        edges = sc.edges
        node_roles = sc.node_roles
        node_priorities = sc.node_priorities
        priority_mode = sc.priority_mode
    else:
        nodes = config.NODES if nodes is None else list(nodes)
        edges = config.EDGES if edges is None else list(edges)
        node_roles = dict(config.NODE_ROLES) if node_roles is None else dict(node_roles)
        node_priorities = {n: 1.0 for n in nodes} if node_priorities is None else dict(node_priorities)

    graph = nx.Graph()
    graph.add_nodes_from(nodes)

    for n in nodes:
        graph.nodes[n]["role"] = node_roles.get(n, "Emergency Node")
        graph.nodes[n]["priority"] = float(node_priorities.get(n, 1.0))

    def calc_eff_weight(u: str, v: str, raw_w: float) -> float:
        p_u = float(node_priorities.get(u, 1.0))
        p_v = float(node_priorities.get(v, 1.0))
        if priority_mode == "product":
            factor = p_u * p_v
        elif priority_mode == "max":
            factor = max(p_u, p_v)
        elif priority_mode == "average":
            factor = (p_u + p_v) / 2.0
        elif priority_mode == "sum":
            factor = p_u + p_v
        else:
            factor = 1.0
        return float(raw_w * factor)

    for edge in edges:
        u, v, weight = edge[0], edge[1], float(edge[2])
        eff_weight = calc_eff_weight(u, v, weight)
        graph.add_edge(u, v, weight=weight, effective_weight=eff_weight)

    return graph
