"""scenario_generator.py - Reproducible synthetic scenario generation.

Generates realistic tactical and emergency wireless mesh topologies with:
- Configurable node counts, channel counts, and edge densities.
- Guaranteed unavoidable interference via embedded cliques (chromatic number > n_channels).
- Operational node priorities and tactical mesh roles.
- Strict disclaimers distinguishing synthetic simulation weights from empirical RF data.
"""

from __future__ import annotations

import argparse
import random
from typing import List, Optional, Tuple

import networkx as nx

from scenario import Scenario

ROLE_POOL = [
    ("Incident Command Post", 3.0),
    ("Medical Triage Unit", 2.5),
    ("Search & Rescue Alpha", 2.0),
    ("Search & Rescue Bravo", 2.0),
    ("Field Hospital", 2.2),
    ("Evacuation Shelter North", 1.5),
    ("Evacuation Shelter South", 1.5),
    ("Logistics Supply Depot", 1.0),
    ("Drone Surveillance Relay", 1.3),
    ("Perimeter Security Post", 1.1),
    ("Water Distribution Point", 1.2),
    ("Helipad Communications", 2.0),
]


def generate_synthetic_scenario(
    n_nodes: int = 8,
    n_channels: int = 3,
    edge_density: float = 0.45,
    weight_range: Tuple[int, int] = (2, 8),
    seed: int = 42,
    force_unavoidable: bool = True,
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> Scenario:
    """Generate a reproducible synthetic wireless mesh interference scenario.

    Parameters:
        n_nodes: Number of communication nodes.
        n_channels: Number of available orthogonal wireless channels.
        edge_density: Erdős-Rényi target edge connection probability (0.0 to 1.0).
        weight_range: (min_weight, max_weight) for synthetic link penalties.
        seed: Random seed for 100% reproducible generation.
        force_unavoidable: If True, injects a clique of size (n_channels + 1)
            so the chromatic number strictly exceeds available channels, guaranteeing
            unavoidable same-channel interference (global minimum > 0).
        name: Name for the scenario.
        description: Description of the scenario.

    Returns:
        Validated Scenario instance.
    """
    rng = random.Random(seed)

    # Node identifiers: A, B, C... or N1, N2...
    if n_nodes <= 26:
        nodes = [chr(65 + i) for i in range(n_nodes)]
    else:
        nodes = [f"N{i+1}" for i in range(n_nodes)]

    channels = list(range(n_channels))

    # Assign tactical roles and priorities
    node_roles = {}
    node_priorities = {}
    for i, node in enumerate(nodes):
        role_idx = i % len(ROLE_POOL)
        role_name, priority = ROLE_POOL[role_idx]
        node_roles[node] = role_name
        node_priorities[node] = priority

    # Generate connected base graph
    # Start with a random tree to guarantee connectivity across the mesh
    G = nx.Graph()
    G.add_nodes_from(nodes)

    unconnected = list(nodes)
    connected = [unconnected.pop(rng.randrange(len(unconnected)))]
    while unconnected:
        u = rng.choice(connected)
        v = unconnected.pop(rng.randrange(len(unconnected)))
        G.add_edge(u, v)

    # Add random edges according to desired density
    possible_edges = [(nodes[i], nodes[j]) for i in range(n_nodes) for j in range(i + 1, n_nodes)]
    for u, v in possible_edges:
        if not G.has_edge(u, v):
            if rng.random() < edge_density:
                G.add_edge(u, v)

    # Force unavoidable interference if requested
    # Embed a clique of size (n_channels + 1)
    if force_unavoidable and n_nodes >= (n_channels + 1):
        clique_size = n_channels + 1
        clique_nodes = nodes[:clique_size]
        for i in range(clique_size):
            for j in range(i + 1, clique_size):
                G.add_edge(clique_nodes[i], clique_nodes[j])

    # Assign synthetic weights
    edges: List[Tuple[str, str, float]] = []
    # Sort edge pairs canonically for deterministic ordering
    for u, v in sorted(G.edges()):
        canon_u, canon_v = sorted([u, v])
        weight = float(rng.randint(weight_range[0], weight_range[1]))
        edges.append((canon_u, canon_v, weight))

    scenario_name = name or f"Synthetic {n_nodes}-Node Mesh ({n_channels} Channels)"
    scenario_desc = description or (
        f"Synthetic {n_nodes}-node emergency mesh with {n_channels} channels. "
        f"{'Unavoidable interference injected via (K_' + str(n_channels+1) + ') clique. ' if force_unavoidable else ''}"
        "All link weights are synthetic simulation heuristics (not empirical RF measurements)."
    )

    scenario = Scenario(
        name=scenario_name,
        nodes=nodes,
        channels=channels,
        edges=edges,
        node_roles=node_roles,
        node_priorities=node_priorities,
        priority_mode="product",
        penalty=None,  # Automatically calculated safe penalty
        is_synthetic=True,
        rf_measurement=False,
        description=scenario_desc,
        metadata={
            "generator": "scenario_generator.py",
            "seed": seed,
            "edge_density": edge_density,
            "force_unavoidable": force_unavoidable,
            "clique_size": (n_channels + 1) if force_unavoidable else None,
        },
    )
    return scenario


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic wireless mesh scenario.")
    parser.add_argument("--nodes", type=int, default=8, help="Number of nodes (default: 8)")
    parser.add_argument("--channels", type=int, default=3, help="Number of channels (default: 3)")
    parser.add_argument("--density", type=float, default=0.45, help="Edge density (default: 0.45)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    parser.add_argument("--out", type=str, default="scenarios/synthetic_8node.json", help="Output JSON path")
    parser.add_argument("--allow-zero-clash", action="store_true", help="Do not force unavoidable interference")
    args = parser.parse_args()

    sc = generate_synthetic_scenario(
        n_nodes=args.nodes,
        n_channels=args.channels,
        edge_density=args.density,
        seed=args.seed,
        force_unavoidable=not args.allow_zero_clash,
    )
    sc.to_json(args.out)
    print(f"Scenario successfully generated and saved to {args.out}")
    print(f"Nodes ({len(sc.nodes)}): {sc.nodes}")
    print(f"Edges ({len(sc.edges)}): {sc.edges}")
    print(f"Penalty P: {sc.penalty}")
