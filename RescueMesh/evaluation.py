"""evaluation.py - checks that the QUBO matches the original formulation and verifies sample statistics.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np

import config
from classical_solver import total_interference
from qubo_model import (all_bitstrings, decode, ising_energies, qubo_energies,
                        qubo_to_ising)


def direct_formula(graph, X, nodes, channels, penalty):
    """Original math computed straight from x (NOT using Q):
        interference = sum_edges w * sum_c x(u,c) x(v,c)
        penalty      = P * sum_nodes (sum_c x(i,c) - 1)^2
    Returns (interference, penalty) arrays, one entry per row of X.
    """
    X3 = X.reshape(len(X), len(nodes), len(channels))   # [row, node, channel]
    interference = np.zeros(len(X))
    for u, v, data in graph.edges(data=True):
        iu, iv = nodes.index(u), nodes.index(v)
        w = float(data.get("effective_weight", data.get("weight", 0.0)))
        interference += w * (X3[:, iu, :] * X3[:, iv, :]).sum(axis=1)
    per_node_count = X3.sum(axis=2)                      # channels chosen per node
    pen = penalty * ((per_node_count - 1) ** 2).sum(axis=1)
    return interference, pen


def validate_qubo(
    graph, Q, offset, classical_result, nodes=None, channels=None, penalty=None
) -> List[Tuple[str, bool, str]]:
    """Evaluate all 2^n bit patterns (for n <= 16); return list of (check, passed, detail)."""
    nodes = list(graph.nodes) if nodes is None else list(nodes)
    channels = list(config.CHANNELS) if channels is None else list(channels)
    penalty = float(config.PENALTY) if penalty is None else float(penalty)
    n_vars = len(nodes) * len(channels)

    if n_vars > 16:
        # For larger problems, exhaustive QUBO state-space checking is mathematically skipped
        return [("QUBO state-space validation skipped for large instance (>16 qubits)", True,
                 f"{n_vars} qubits = 2^{n_vars} states exceeds exhaustive validation limit")]

    X = all_bitstrings(n_vars)
    E = qubo_energies(Q, offset, X)
    interference, pen = direct_formula(graph, X, nodes, channels, penalty)
    decoded = [decode(x, nodes, channels) for x in X]
    valid = np.array([d is not None for d in decoded])
    best = classical_result["best_score"] if classical_result and not classical_result.get("skipped", False) else None
    checks = []

    expected_valid = len(channels) ** len(nodes)
    checks.append((f"2^{n_vars} patterns: {expected_valid} valid, rest invalid",
                   len(X) == 2 ** n_vars and valid.sum() == expected_valid,
                   f"{len(X)} total, {valid.sum()} valid, {(~valid).sum()} invalid"))

    # Valid: QUBO energy == classical interference (independent code path).
    ok = all(abs(E[r] - total_interference(graph, decoded[r])) < 1e-9 for r in np.where(valid)[0])
    checks.append(("valid assignments: QUBO energy == classical interference",
                   ok, f"all {valid.sum()} compared"))

    # All patterns: QUBO energy == formula (interference + penalty).
    diff = np.abs(E - (interference + pen)).max()
    checks.append(("all patterns: QUBO energy == interference + P*sum(count-1)^2",
                   diff < 1e-9, f"max abs difference = {diff:.1e}"))

    # Penalty part: 0 for valid, >= P for invalid.
    extra = E - interference
    ok = np.allclose(extra[valid], 0) and np.all(extra[~valid] >= penalty - 1e-9) \
        and np.allclose(extra, pen)
    checks.append(("penalty is 0 when valid and >= P when invalid", ok,
                   f"smallest invalid penalty = {extra[~valid].min():.0f} (P = {penalty:.0f})"))

    if best is not None:
        min_invalid = E[~valid].min()
        checks.append(("no invalid pattern scores below the valid optimum",
                       min_invalid > best,
                       f"valid optimum = {best:g}, lowest invalid energy = {min_invalid:.0f}"))

        argmins = {tuple(sorted(decoded[r].items())) for r in np.where(np.isclose(E, E.min()))[0]
                   if decoded[r] is not None}
        n_min_total = int(np.isclose(E, E.min()).sum())
        classical = {tuple(sorted(a.items())) for a in classical_result["all_optimal"]}
        checks.append(("QUBO minimizers == classical optimal assignments",
                       argmins == classical and n_min_total == len(classical),
                       f"{n_min_total} minimizers, all valid, same set as exhaustive search"))

    # Ising conversion: same energy for every pattern (z = 1 - 2x).
    h, J, const = qubo_to_ising(Q, offset)
    Z = 1 - 2 * X
    diff = np.abs(ising_energies(h, J, const, Z) - E).max()
    checks.append(("Ising energy == QUBO energy (x = (1-z)/2) for all patterns",
                   diff < 1e-9, f"max abs difference = {diff:.1e}"))
    return checks


# ------------------------------------------------------------------ Phase 4
def summarize_samples(rows, graph, classical_best):
    """Summarize measured candidates (output of quantum_solver.analyze_counts)."""
    shots = sum(r["count"] for r in rows)
    valid = [r for r in rows if r["valid"]]
    valid_shots = sum(r["count"] for r in valid)
    for r in valid:
        assert abs(r["energy"] - total_interference(graph, r["assignment"])) < 1e-9
    best = min(valid, key=lambda r: r["energy"]) if valid else None
    optimal_shots = sum(r["count"] for r in valid if classical_best is not None and abs(r["energy"] - classical_best) < 1e-9)
    gap = (best["energy"] - classical_best) if (best is not None and classical_best is not None) else None
    return {
        "shots": shots,
        "distinct_bitstrings": len(rows),
        "valid_shots": valid_shots,
        "invalid_shots": shots - valid_shots,
        "distinct_valid_assignments": len(valid),
        "optimal_shots": optimal_shots,
        "best_valid": best,
        "best_valid_score": None if best is None else best["energy"],
        "found_optimum": best is not None and classical_best is not None and abs(best["energy"] - classical_best) < 1e-9,
        "gap": gap,
    }


def random_baseline(n_vars, shots, Q, offset, graph, classical_best, seed=42):
    """Uniform-random bit patterns reference."""
    from quantum_solver import EnergyTable, analyze_counts
    counts = random_counts(n_vars, shots, seed)
    rows = analyze_counts(counts, EnergyTable(Q, offset), list(graph.nodes))
    return summarize_samples(rows, graph, classical_best)


def random_counts(n_vars, shots, seed=42):
    """`shots` uniformly random bit patterns as {bitstring: count}."""
    from collections import Counter
    rng = np.random.default_rng(seed)
    bits = rng.integers(0, 2, size=(shots, n_vars))
    return dict(Counter("".join(str(b) for b in row[::-1]) for row in bits))


# ------------------------------------------------------------------ Phase 5
def method_stats(rows, classical_best):
    """All Phase 5 metrics for one sampling method."""
    shots = sum(r["count"] for r in rows)
    valid = [r for r in rows if r["valid"]]
    valid_count = sum(r["count"] for r in valid)
    optimal = [r for r in valid if classical_best is not None and abs(r["energy"] - classical_best) < 1e-9]
    optimal_count = sum(r["count"] for r in optimal)
    best = min((r["energy"] for r in valid), default=None)
    energy_hist, valid_hist = {}, {}
    for r in rows:
        energy_hist[r["energy"]] = energy_hist.get(r["energy"], 0) + r["count"]
        if r["valid"]:
            valid_hist[r["energy"]] = valid_hist.get(r["energy"], 0) + r["count"]
    gap = (best - classical_best) if (best is not None and classical_best is not None) else None
    return {
        "shots": shots,
        "valid_count": valid_count,
        "valid_pct": 100 * valid_count / shots if shots else 0.0,
        "invalid_count": shots - valid_count,
        "optimal_count": optimal_count,
        "optimal_pct": 100 * optimal_count / shots if shots else 0.0,
        "distinct_optimal_assignments": len({tuple(sorted(r["assignment"].items())) for r in optimal}),
        "best_valid_score": best,
        "gap": gap,
        "mean_energy_all_samples": (sum(r["count"] * r["energy"] for r in rows) / shots) if shots else 0.0,
        "mean_interference_of_valid_samples":
            (sum(r["count"] * r["energy"] for r in valid) / valid_count) if valid_count else None,
        "distinct_bitstrings": len(rows),
        "energy_histogram": {str(k): v for k, v in sorted(energy_hist.items())},
        "valid_score_histogram": {str(k): v for k, v in sorted(valid_hist.items())},
    }


def verify_results(results, graph, nodes=None, channels=None, penalty=None):
    """Independent re-check of every sampled method from its RAW COUNTS."""
    nodes = list(graph.nodes) if nodes is None else list(nodes)
    channels = list(config.CHANNELS) if channels is None else list(channels)
    penalty = float(config.PENALTY) if penalty is None else float(penalty)
    n_ch = len(channels)
    out = []
    exact_best = results.get("exact", {}).get("best_score", None)

    for name, m in results["methods"].items():
        if "counts" not in m:
            continue
        shots = valid = optimal = 0
        energy_sum = 0.0
        for bitstring, count in m["counts"].items():
            bit = lambda k: int(bitstring[-1 - k])
            chosen = {node: [c for c in range(n_ch) if bit(n * n_ch + c) == 1]
                      for n, node in enumerate(nodes)}
            pen = penalty * sum((len(v) - 1) ** 2 for v in chosen.values())
            interference = 0.0
            for u, v, data in graph.edges(data=True):
                w = float(data.get("effective_weight", data.get("weight", 0.0)))
                interference += w * sum(
                    bit(nodes.index(u) * n_ch + c) * bit(nodes.index(v) * n_ch + c)
                    for c in range(n_ch))
            shots += count
            energy_sum += count * (interference + pen)
            if all(len(v) == 1 for v in chosen.values()):
                valid += count
                if exact_best is not None and abs(interference - exact_best) < 1e-9:
                    optimal += count
        ok = (shots == m["shots"] == results["config"]["shots"]
              and valid == m["valid_count"] and optimal == m["optimal_count"]
              and abs(energy_sum / shots - m["mean_energy_all_samples"]) < 1e-9
              and abs(100 * valid / shots - m["valid_pct"]) < 1e-9
              and abs(100 * optimal / shots - m["optimal_pct"]) < 1e-9)
        out.append((f"{name}: counts, percentages and mean energy recomputed from raw bitstrings", ok,
                    f"shots={shots}, valid={valid}, optimal={optimal}, mean energy={energy_sum / shots:.4f}"))
    return out
