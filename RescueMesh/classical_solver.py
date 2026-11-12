"""classical_solver.py - Classical solvers for wireless channel allocation.

Includes:
1. Exact exhaustive search for manageable instances.
2. Fast deterministic/multi-start greedy allocation (priority & degree-guided).
3. Simulated annealing heuristic for larger topologies.
4. Optimality gap analysis against the exact global minimum.
"""

from __future__ import annotations

import math
import random
import time
from itertools import product
from typing import Any, Dict, Generator, List, Optional, Tuple, Union

import networkx as nx

import config


def generate_assignments(
    nodes: List[str], channels: List[Union[int, str]]
) -> Generator[Dict[str, Union[int, str]], None, None]:
    """Yield every valid channel assignment as a dict, e.g. {"A": 0, "B": 2, ...}."""
    for combo in product(channels, repeat=len(nodes)):
        yield dict(zip(nodes, combo))


def edge_interference(graph: nx.Graph, assignment: Dict[str, Any]) -> Dict[Tuple[str, str], float]:
    """Interference paid by each edge, as {(u, v): cost}.

    An edge costs its effective weight if both ends use the same channel, else 0.
    """
    costs = {}
    for u, v, data in graph.edges(data=True):
        same_channel = assignment[u] == assignment[v]
        w = float(data.get("effective_weight", data.get("weight", 0.0)))
        costs[(u, v)] = w if same_channel else 0.0
    return costs


def total_interference(graph: nx.Graph, assignment: Dict[str, Any]) -> float:
    """Total interference = sum of all edge clash costs."""
    return sum(edge_interference(graph, assignment).values())


def interference_from_binary_variables(
    graph: nx.Graph, assignment: Dict[str, Any], channels: List[Any]
) -> float:
    """Independent mathematical cross-check using binary variables x(i,c):

        sum over edges (i,j) of  w_ij * sum over channels c of  x(i,c) * x(j,c)
    """
    x = {(i, c): int(assignment[i] == c) for i in assignment for c in channels}
    total = 0.0
    for u, v, data in graph.edges(data=True):
        w = float(data.get("effective_weight", data.get("weight", 0.0)))
        total += w * sum(x[(u, c)] * x[(v, c)] for c in channels)
    return total


# ------------------------------------------------------------- Exact Exhaustive
def solve_exhaustive(
    graph: nx.Graph,
    nodes: Optional[List[str]] = None,
    channels: Optional[List[Any]] = None,
    max_combinations: int = 500_000,
) -> Dict[str, Any]:
    """Try all assignments and return the exact global optimum.

    Guards against state-space explosion if |channels|^|nodes| > max_combinations.
    """
    nodes = list(graph.nodes) if nodes is None else list(nodes)
    channels = list(config.CHANNELS) if channels is None else list(channels)

    total_combinations = len(channels) ** len(nodes)
    if total_combinations > max_combinations:
        return {
            "skipped": True,
            "reason": (
                f"State space {len(channels)}^{len(nodes)} = {total_combinations} "
                f"exceeds exhaustive limit ({max_combinations})."
            ),
            "best_assignment": None,
            "best_score": None,
            "all_optimal": [],
            "all_scores": [],
            "runtime_seconds": 0.0,
        }

    t0 = time.perf_counter()
    all_scores = []
    for assignment in generate_assignments(nodes, channels):
        score = total_interference(graph, assignment)
        all_scores.append((assignment, score))

    best_score = min(score for _, score in all_scores)
    all_optimal = [a for a, score in all_scores if score == best_score]
    runtime = time.perf_counter() - t0

    return {
        "skipped": False,
        "best_assignment": all_optimal[0],
        "best_score": best_score,
        "all_optimal": all_optimal,
        "all_scores": all_scores,
        "runtime_seconds": runtime,
    }


def validate_solution(
    graph: nx.Graph,
    result: Dict[str, Any],
    nodes: Optional[List[str]] = None,
    channels: Optional[List[Any]] = None,
) -> List[Tuple[str, bool]]:
    """Verify consistency of exhaustive search results."""
    if result.get("skipped", False):
        return [("exhaustive search was skipped (space too large)", True)]

    nodes = list(graph.nodes) if nodes is None else list(nodes)
    channels = list(config.CHANNELS) if channels is None else list(channels)
    all_scores = result["all_scores"]
    checks = []

    # 1. Total assignments enumerated
    expected = len(channels) ** len(nodes)
    unique = {tuple(sorted(a.items())) for a, _ in all_scores}
    checks.append((f"enumerated {expected} distinct assignments",
                   len(all_scores) == expected and len(unique) == expected))

    # 2. Every node has exactly one valid channel
    checks.append(("every node has exactly one channel (all assignments)",
                   all(set(a) == set(nodes) and all(a[n] in channels for n in nodes)
                       for a, _ in all_scores)))

    # 3. Edge-based score equals formula
    checks.append(("edge-based score == x(i,c) formula (all assignments)",
                   all(abs(score - interference_from_binary_variables(graph, a, channels)) < 1e-9
                       for a, score in all_scores)))

    # 4. No assignment beats best score
    best = result["best_score"]
    checks.append(("no assignment scores below the reported minimum",
                   all(score >= best - 1e-9 for _, score in all_scores)))

    # 5. Best assignment achieves reported minimum
    checks.append(("reported assignment achieves the reported minimum",
                   abs(total_interference(graph, result["best_assignment"]) - best) < 1e-9))

    # 6. Channel permutation symmetry check (if graph is unconstrained across channels)
    factorial = 1
    for k in range(2, len(channels) + 1):
        factorial *= k
    checks.append((f"number of optimal assignments is a multiple of {factorial}",
                   len(result["all_optimal"]) % factorial == 0))
    return checks


# ------------------------------------------------------------- Greedy Solver
def solve_greedy(
    graph: nx.Graph,
    nodes: Optional[List[str]] = None,
    channels: Optional[List[Any]] = None,
    seed: Optional[int] = None,
    order_strategy: str = "priority_degree",
) -> Dict[str, Any]:
    """Greedy channel allocation algorithm.

    Sorts nodes by priority descending, then weighted degree descending,
    and assigns each node the channel that causes minimum incremental interference.

    Parameters:
        graph: NetworkX interference graph.
        nodes: List of node names.
        channels: List of channels.
        seed: Random seed for tie-breaking.
        order_strategy: 'priority_degree', 'degree', or 'random'.
    """
    t0 = time.perf_counter()
    nodes = list(graph.nodes) if nodes is None else list(nodes)
    channels = list(config.CHANNELS) if channels is None else list(channels)

    rng = random.Random(seed) if seed is not None else random.Random(42)

    # Calculate node priorities and weighted degrees
    node_weights = {}
    for n in nodes:
        priority = float(graph.nodes[n].get("priority", 1.0))
        weighted_deg = sum(
            float(data.get("effective_weight", data.get("weight", 0.0)))
            for _, _, data in graph.edges(n, data=True)
        )
        node_weights[n] = (priority, weighted_deg)

    if order_strategy == "priority_degree":
        sorted_nodes = sorted(nodes, key=lambda n: (node_weights[n][0], node_weights[n][1]), reverse=True)
    elif order_strategy == "degree":
        sorted_nodes = sorted(nodes, key=lambda n: node_weights[n][1], reverse=True)
    elif order_strategy == "random":
        sorted_nodes = list(nodes)
        rng.shuffle(sorted_nodes)
    else:
        sorted_nodes = list(nodes)

    assignment: Dict[str, Any] = {}

    for u in sorted_nodes:
        best_ch = None
        best_incremental = float("inf")
        candidate_channels = list(channels)
        # Deterministic shuffle or sort
        if seed is not None:
            rng.shuffle(candidate_channels)

        for ch in candidate_channels:
            inc_cost = 0.0
            for v in graph.neighbors(u):
                if v in assignment and assignment[v] == ch:
                    inc_cost += float(graph[u][v].get("effective_weight", graph[u][v].get("weight", 0.0)))
            if inc_cost < best_incremental:
                best_incremental = inc_cost
                best_ch = ch

        assignment[u] = best_ch

    runtime = time.perf_counter() - t0
    score = total_interference(graph, assignment)

    return {
        "best_assignment": assignment,
        "best_score": score,
        "runtime_seconds": runtime,
        "order": sorted_nodes,
        "strategy": order_strategy,
    }


# -------------------------------------------------------- Simulated Annealing
def solve_simulated_annealing(
    graph: nx.Graph,
    nodes: Optional[List[str]] = None,
    channels: Optional[List[Any]] = None,
    initial_temp: float = 15.0,
    cooling_rate: float = 0.995,
    max_steps: int = 8000,
    seed: int = 42,
    start_from_greedy: bool = False,
) -> Dict[str, Any]:
    """Simulated Annealing heuristic for channel allocation.

    Maintains a strictly valid allocation vector throughout and optimizes via
    Metropolis transitions with geometric cooling.

    Parameters:
        graph: NetworkX interference graph.
        nodes: List of node names.
        channels: List of channels.
        initial_temp: Starting temperature T_0.
        cooling_rate: Geometric cooling decay factor alpha (e.g. 0.995).
        max_steps: Number of transition attempts.
        seed: Random seed for 100% reproducibility.
        start_from_greedy: Initialize from greedy solution instead of random.
    """
    t0 = time.perf_counter()
    nodes = list(graph.nodes) if nodes is None else list(nodes)
    channels = list(config.CHANNELS) if channels is None else list(channels)

    rng = random.Random(seed)

    # Initial state
    if start_from_greedy:
        greedy_res = solve_greedy(graph, nodes, channels, seed=seed)
        current_state = dict(greedy_res["best_assignment"])
    else:
        current_state = {n: rng.choice(channels) for n in nodes}

    current_energy = total_interference(graph, current_state)
    best_state = dict(current_state)
    best_energy = current_energy

    temp = initial_temp
    accepted_moves = 0

    for step in range(max_steps):
        # Pick random node
        node = rng.choice(nodes)
        curr_ch = current_state[node]

        other_channels = [c for c in channels if c != curr_ch]
        if not other_channels:
            break
        new_ch = rng.choice(other_channels)

        # Compute delta energy incrementally: only incident edges of 'node' change
        old_cost = 0.0
        new_cost = 0.0
        for neighbor in graph.neighbors(node):
            neigh_ch = current_state[neighbor]
            w = float(graph[node][neighbor].get("effective_weight", graph[node][neighbor].get("weight", 0.0)))
            if neigh_ch == curr_ch:
                old_cost += w
            if neigh_ch == new_ch:
                new_cost += w

        delta = new_cost - old_cost

        # Metropolis criterion
        if delta <= 0 or (temp > 1e-9 and rng.random() < math.exp(-delta / temp)):
            current_state[node] = new_ch
            current_energy += delta
            accepted_moves += 1
            if current_energy < best_energy:
                best_energy = current_energy
                best_state = dict(current_state)

        temp *= cooling_rate
        if temp < 1e-8 and best_energy == 0:
            break

    runtime = time.perf_counter() - t0

    # Ensure best_state achieves reported best_energy
    rechecked = total_interference(graph, best_state)

    return {
        "best_assignment": best_state,
        "best_score": rechecked,
        "runtime_seconds": runtime,
        "steps_executed": step + 1,
        "accepted_moves": accepted_moves,
        "seed": seed,
    }


# ------------------------------------------------------------- Optimality Gap
def compute_optimality_gap(
    score: Optional[float], exact_best: Optional[float]
) -> Dict[str, Any]:
    """Compute absolute and relative optimality gap against an exact baseline."""
    if score is None or exact_best is None:
        return {
            "absolute_gap": None,
            "relative_gap_pct": None,
            "is_optimal": None,
            "gap_str": "N/A (exact optimum not available)",
        }

    abs_gap = float(score - exact_best)
    is_optimal = abs(abs_gap) < 1e-9

    if exact_best > 0:
        rel_pct = (abs_gap / exact_best) * 100.0
        gap_str = f"+{abs_gap:.2f} ({rel_pct:.2f}% gap)" if not is_optimal else "0.00 (optimal)"
    else:
        rel_pct = 0.0 if is_optimal else None
        gap_str = f"+{abs_gap:.2f} (exact optimum = 0)" if not is_optimal else "0.00 (optimal)"

    return {
        "absolute_gap": abs_gap,
        "relative_gap_pct": rel_pct,
        "is_optimal": is_optimal,
        "gap_str": gap_str,
    }
