"""visualization.py - Matplotlib/NetworkX plots for network topology and optimization results.

Provides:
- draw_network: Draw base topology or channel-allocated mesh with highlighted clashes.
- draw_allocated_network: Specialized visualization of assigned channels with clash indicators.
- plot_phase5: Comparative bar charts, energy histograms, and runtimes.
- draw_architecture: Visual diagram of the classical-quantum hybrid workflow.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Union

import matplotlib
matplotlib.use("Agg")                  # draw to files, no GUI window needed
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

import config

CHANNEL_COLORS = [
    "#1f77b4",  # Channel 0: Blue
    "#ff7f0e",  # Channel 1: Orange
    "#2ca02c",  # Channel 2: Green
    "#9467bd",  # Channel 3: Purple
    "#8c564b",  # Channel 4: Brown
    "#e377c2",  # Channel 5: Pink
    "#7f7f7f",  # Channel 6: Gray
    "#bcbd22",  # Channel 7: Olive
    "#17becf",  # Channel 8: Cyan
]


def draw_allocated_network(
    graph: nx.Graph,
    assignment: Dict[str, Any],
    filename: str = "results/allocated_network.png",
    title: Optional[str] = None,
    seed: int = 42,
) -> str:
    """Draw the network topology colored by allocated channel with clash highlights.

    Nodes:
        Colored according to their assigned channel.

    Edges:
        - Same-channel clash: Highlighted in bold vivid red/crimson with cost label.
        - Resolved interference: Rendered in muted gray with zero cost paid.

    Saves the visualization automatically and returns the filepath.
    """
    os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
    pos = nx.spring_layout(graph, seed=seed, weight=None)

    channels = sorted(list(set(assignment.values())))
    ch_to_color = {ch: CHANNEL_COLORS[i % len(CHANNEL_COLORS)] for i, ch in enumerate(channels)}

    node_colors = [ch_to_color[assignment[n]] for n in graph.nodes]

    fig, ax = plt.subplots(figsize=(10, 7.5))

    # Separate edges into clashing (same channel) and resolved (different channels)
    clash_edges = []
    clash_weights = []
    resolved_edges = []

    for u, v, data in graph.edges(data=True):
        w = float(data.get("effective_weight", data.get("weight", 1.0)))
        if assignment[u] == assignment[v]:
            clash_edges.append((u, v))
            clash_weights.append(w)
        else:
            resolved_edges.append((u, v))

    # Draw resolved edges: thin, muted gray dashed
    if resolved_edges:
        nx.draw_networkx_edges(
            graph, pos, edgelist=resolved_edges,
            width=1.2, edge_color="#b0bec5", style="dashed", alpha=0.7, ax=ax
        )

    # Draw clash edges: bold crimson, thick
    if clash_edges:
        widths = [max(2.5, min(7.0, 0.8 * w)) for w in clash_weights]
        nx.draw_networkx_edges(
            graph, pos, edgelist=clash_edges,
            width=widths, edge_color="#d32f2f", style="solid", alpha=0.95, ax=ax
        )

    # Draw nodes
    nx.draw_networkx_nodes(
        graph, pos, node_size=1600, node_color=node_colors,
        edgecolors="black", linewidths=2.0, ax=ax
    )

    # Node labels: Node ID + Channel
    labels = {n: f"{n}\nCh {assignment[n]}" for n in graph.nodes}
    nx.draw_networkx_labels(graph, pos, labels=labels, font_size=11, font_weight="bold", ax=ax)

    # Edge labels: only label clash edges clearly with penalty, or all edges with weights
    edge_labels = {}
    for u, v in clash_edges:
        w = graph[u][v].get("effective_weight", graph[u][v].get("weight", 1.0))
        edge_labels[(u, v)] = f"CLASH ({w:g})"
    for u, v in resolved_edges:
        w = graph[u][v].get("effective_weight", graph[u][v].get("weight", 1.0))
        edge_labels[(u, v)] = f"{w:g}"

    nx.draw_networkx_edge_labels(
        graph, pos, edge_labels=edge_labels,
        font_size=9, font_color="#37474f", ax=ax,
        bbox=dict(boxstyle="round,pad=0.2", facecolor="white", edgecolor="#cfd8dc", alpha=0.85)
    )

    # Total score calculation
    total_cost = sum(clash_weights)
    clash_count = len(clash_edges)

    # Build legend
    legend_lines = [f"Total Interference: {total_cost:g}", f"Active Clashes: {clash_count}", "--- Channels ---"]
    for ch in channels:
        nodes_on_ch = [n for n, c in assignment.items() if c == ch]
        legend_lines.append(f"Ch {ch} ({len(nodes_on_ch)} nodes): {', '.join(nodes_on_ch)}")

    legend_lines.append("--- Node Roles & Priorities ---")
    for n in sorted(graph.nodes):
        role = graph.nodes[n].get("role", "Node")
        pri = graph.nodes[n].get("priority", 1.0)
        pri_str = f" [p={pri:g}]" if pri != 1.0 else ""
        legend_lines.append(f"{n}: {role}{pri_str}")

    legend_text = "\n".join(legend_lines)
    ax.text(
        1.02, 0.5, legend_text, transform=ax.transAxes, va="center", fontsize=9,
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#f8f9fa", edgecolor="#b0bec5")
    )

    title_str = title or (
        f"RescueMesh Channel Allocation\n"
        f"Nodes colored by channel | Red edges = active same-channel interference ({clash_count} clashes, cost={total_cost:g})"
    )
    ax.set_title(title_str, fontsize=12, fontweight="bold", pad=12)
    ax.axis("off")

    fig.savefig(filename, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return filename


def draw_network(
    graph: nx.Graph,
    filename: str = "results/network_graph.png",
    assignment: Optional[Dict[str, Any]] = None,
    title: Optional[str] = None,
) -> str:
    """Draw the interference graph; if assignment is provided, highlights channels and clashes."""
    if assignment is not None:
        return draw_allocated_network(graph, assignment, filename=filename, title=title)

    os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
    pos = nx.spring_layout(graph, seed=42, weight=None)
    weights = [float(graph[u][v].get("weight", 1.0)) for u, v in graph.edges]

    fig, ax = plt.subplots(figsize=(8.5, 6))
    nx.draw_networkx_nodes(graph, pos, node_size=1400, node_color="#9ecae1",
                           edgecolors="black", ax=ax)
    nx.draw_networkx_labels(graph, pos, font_size=14, font_weight="bold", ax=ax)

    max_w = max(weights) if weights else 1.0
    nx.draw_networkx_edges(graph, pos, width=[max(1.0, 0.6 * w) for w in weights],
                           edge_color=weights, edge_cmap=plt.cm.Reds,
                           edge_vmin=0, edge_vmax=max_w, ax=ax)
    nx.draw_networkx_edge_labels(
        graph, pos,
        edge_labels={(u, v): f"{graph[u][v].get('weight', 1.0):g}" for u, v in graph.edges},
        font_size=11, ax=ax)

    legend_items = []
    for n in sorted(graph.nodes):
        role = graph.nodes[n].get("role", config.NODE_ROLES.get(n, "Node"))
        pri = graph.nodes[n].get("priority", 1.0)
        pri_str = f" (pri {pri:g})" if pri != 1.0 else ""
        legend_items.append(f"{n}: {role}{pri_str}")

    legend = "\n".join(legend_items)
    ax.text(1.02, 0.5, legend, transform=ax.transAxes, va="center", fontsize=9.5,
            bbox=dict(boxstyle="round", facecolor="white", edgecolor="gray"))
    t = title or ("RescueMesh: weighted interference graph\n"
                  "(edge label = synthetic interference cost if both nodes share a channel)")
    ax.set_title(t, fontsize=12)
    ax.axis("off")
    fig.savefig(filename, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return filename


# ------------------------------------------------------------------ Phase 5
COLORS = {"Random sampling": "#9e9e9e", "QAOA p=1": "#1f77b4", "QAOA p=2": "#ff7f0e"}


def _style(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.3)
    ax.set_axisbelow(True)


def _bar_panel(ax, results, key_count, key_pct, ylabel, title):
    names = list(results["methods"])
    shots = results["config"]["shots"]
    vals = [results["methods"][n][key_pct] for n in names]
    bars = ax.bar(names, vals, color=[COLORS.get(n, "#5c6bc0") for n in names], edgecolor="black")
    for bar, n in zip(bars, names):
        c = results["methods"][n][key_count]
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                f"{c} / {shots}\n({results['methods'][n][key_pct]:.2f}%)",
                ha="center", va="bottom", fontsize=10)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.set_ylim(0, max(vals) * 1.25 if vals and max(vals) > 0 else 1.0)
    _style(ax)


def plot_phase5(results: Dict[str, Any], outdir: str = "results") -> List[str]:
    """Create the five Phase 5 figures from results dict. Returns file names."""
    os.makedirs(outdir, exist_ok=True)
    names = list(results["methods"])
    shots = results["config"]["shots"]
    files = []

    # 1. valid-solution rate
    fig, ax = plt.subplots(figsize=(7, 5))
    _bar_panel(ax, results, "valid_count", "valid_pct", "% of samples that are valid",
               f"Valid allocations (each node has exactly one channel)\n{shots} samples per method")
    f = f"{outdir}/fig1_valid_rates.png"; fig.savefig(f, dpi=150, bbox_inches="tight"); plt.close(fig); files.append(f)

    # 2. optimal-solution rate
    fig, ax = plt.subplots(figsize=(7, 5))
    best_exact = results.get("exact", {}).get("best_score", 0)
    _bar_panel(ax, results, "optimal_count", "optimal_pct",
               f"% of samples that are optimal (score {best_exact:g})",
               f"Optimal allocations found\n{shots} samples per method")
    f = f"{outdir}/fig2_optimal_rates.png"; fig.savefig(f, dpi=150, bbox_inches="tight"); plt.close(fig); files.append(f)

    # 3. energy distributions
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    max_e = max(float(k) for n in names for k in results["methods"][n]["energy_histogram"])
    bins = np.arange(0, max_e + 10, 10)
    for n in names:
        h = results["methods"][n]["energy_histogram"]
        e = np.array([float(k) for k in h]); w = np.array([h[k] for k in h]) / shots * 100
        ax1.hist(e, bins=bins, weights=w, histtype="step", linewidth=2, color=COLORS.get(n, "#5c6bc0"), label=n)
        ax1.axvline(results["methods"][n]["mean_energy_all_samples"], color=COLORS.get(n, "#5c6bc0"), ls=":", alpha=0.8)
    ax1.set_xlabel("QUBO energy of the measured bitstring (dotted = mean)")
    ax1.set_ylabel("% of samples (bins of width 10)")
    ax1.set_title("All samples: QAOA shifts probability toward lower energy")
    ax1.legend(); _style(ax1)
    scores = sorted({int(float(k)) for n in names for k in results["methods"][n]["valid_score_histogram"]})
    width = 0.8 / len(names) if names else 0.4
    for i, n in enumerate(names):
        h = results["methods"][n]["valid_score_histogram"]
        ax2.bar(np.array(scores) + (i - (len(names) - 1) / 2) * width,
                [h.get(str(float(s)), h.get(str(s), 0)) for s in scores], width=width,
                color=COLORS.get(n, "#5c6bc0"), edgecolor="black", label=f"{n} ({results['methods'][n]['valid_count']} valid)")
    ax2.set_xlabel("Interference score of VALID samples")
    ax2.set_ylabel("Number of valid samples (raw counts)")
    ax2.set_title("Valid samples only")
    ax2.legend(); _style(ax2)
    f = f"{outdir}/fig3_energy_distribution.png"; fig.savefig(f, dpi=150, bbox_inches="tight"); plt.close(fig); files.append(f)

    # 4. classical optimum vs best QAOA result
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    exact_score = results.get("exact", {}).get("best_score", 0.0)
    labels = ["Exhaustive\n(exact)"] + names
    best = [exact_score] + [results["methods"][n]["best_valid_score"] for n in names]
    cols = ["#2ca02c"] + [COLORS.get(n, "#5c6bc0") for n in names]
    ax1.bar(labels, best, color=cols, edgecolor="black")
    for i, v in enumerate(best):
        val_str = f"{v:g}" if v is not None else "N/A"
        y_pos = (v if v is not None else 0) + 0.05
        ax1.text(i, y_pos, val_str, ha="center", fontsize=11)
    ax1.axhline(exact_score, color="green", ls="--", label="exact global minimum")
    max_b = max([b for b in best if b is not None] + [1.0])
    ax1.set_ylim(0, max_b * 1.25)
    ax1.set_ylabel("Best valid interference score (lower = better)")
    ax1.set_title("Best valid result comparison")
    ax1.legend(); _style(ax1)

    labels2 = ["All valid\n(uniform)"] + names
    mean_exact = results.get("exact", {}).get("mean_interference_over_valid", 0.0)
    mean_valid = [mean_exact] + [results["methods"][n]["mean_interference_of_valid_samples"] for n in names]
    ax2.bar(labels2, mean_valid, color=["#2ca02c"] + [COLORS.get(n, "#5c6bc0") for n in names], edgecolor="black")
    for i, v in enumerate(mean_valid):
        val_str = f"{v:.2f}" if v is not None else "N/A"
        y_pos = (v if v is not None else 0) + 0.1
        ax2.text(i, y_pos, val_str, ha="center", fontsize=11)
    ax2.set_ylabel("Mean interference of valid samples")
    ax2.set_title("Average quality of valid samples")
    _style(ax2)
    f = f"{outdir}/fig4_best_vs_optimum.png"; fig.savefig(f, dpi=150, bbox_inches="tight"); plt.close(fig); files.append(f)

    # 5. runtime (log scale)
    rt = results["runtime_seconds"]
    labels = ["Exhaustive", f"Random ({shots})", f"QAOA p=1\nsample ({shots})"]
    vals = [rt.get("exhaustive", 0.001), rt.get("random_sampling", 0.01), rt.get("qaoa_p1_sampling", 0.01)]
    cols = ["#2ca02c", COLORS.get("Random sampling", "#9e9e9e"), COLORS.get("QAOA p=1", "#1f77b4")]

    if "qaoa_p1_optimization" in rt:
        evals = results["methods"].get("QAOA p=1", {}).get("optimization", {}).get("evaluations", "")
        labels.append(f"QAOA p=1\nopt ({evals} runs)")
        vals.append(rt["qaoa_p1_optimization"])
        cols.append(COLORS.get("QAOA p=1", "#1f77b4"))

    if "QAOA p=2" in results["methods"] and "qaoa_p2_optimization" in rt:
        evals2 = results["methods"].get("QAOA p=2", {}).get("optimization", {}).get("evaluations", "")
        labels.append(f"QAOA p=2\nopt ({evals2} runs)")
        vals.append(rt["qaoa_p2_optimization"])
        cols.append(COLORS.get("QAOA p=2", "#ff7f0e"))

    fig, ax = plt.subplots(figsize=(10, 5.5))
    bars = ax.bar(labels, vals, color=cols, edgecolor="black")
    ax.set_yscale("log")
    for b, v in zip(bars, vals):
        v_str = f"{v:.3g} s" if v >= 0.01 else f"{v*1000:.1f} ms"
        ax.text(b.get_x() + b.get_width() / 2, v * 1.15, v_str, ha="center", fontsize=10)
    ax.set_ylabel("Wall-clock time in seconds (log scale)")
    ax.set_title("Runtime comparison. QAOA times are classical CPU SIMULATION,\nnot quantum hardware execution.")
    ax.tick_params(axis="x", labelsize=8); _style(ax)
    f = f"{outdir}/fig5_runtime.png"; fig.savefig(f, dpi=150, bbox_inches="tight"); plt.close(fig); files.append(f)
    return files


# ------------------------------------------------------- architecture diagram
def draw_architecture(filename="report/architecture_diagram.png"):
    """Draw the RescueMesh pipeline: classical (blue), quantum (purple) and the
    independent classical baseline (green). Pure Matplotlib, no data needed."""
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle
    os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)

    BLUE, PURPLE, GREEN, GREY = "#cfe2f3", "#e1d5f0", "#d5ecd4", "#eeeeee"
    EDGE = {BLUE: "#2a6099", PURPLE: "#6a3d9a", GREEN: "#2e7d32", GREY: "#666666"}
    fig, ax = plt.subplots(figsize=(16, 9.6))
    ax.set_xlim(0, 16); ax.set_ylim(0, 10); ax.axis("off")

    # lane backgrounds
    ax.add_patch(Rectangle((6.45, 3.75), 9.45, 3.0, color="#f3ecfa", zorder=0))
    ax.text(6.6, 6.55, "QUANTUM BRANCH  (Qiskit circuit, Aer simulator)", fontsize=10,
            color="#6a3d9a", fontweight="bold", va="top")
    ax.add_patch(Rectangle((0.2, 3.75), 6.0, 3.0, color="#eef7ee", zorder=0))
    ax.text(0.35, 6.55, "INDEPENDENT CLASSICAL BASELINES  (Greedy, SA, Exhaustive)", fontsize=10,
            color="#2e7d32", fontweight="bold", va="top")

    def box(x, y, w, h, title, body, color, number=None):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.04,rounding_size=0.12",
                                    facecolor=color, edgecolor=EDGE[color], linewidth=1.8, zorder=2))
        head = f"{number}. {title}" if number else title
        ax.text(x + w / 2, y + h - 0.2, head, ha="center", va="top", fontsize=10.5,
                fontweight="bold", zorder=3)
        ax.text(x + w / 2, y + h - 0.62, body, ha="center", va="top", fontsize=8.6, zorder=3,
                linespacing=1.35)

    def arrow(p, q, color="#333333", both=False, style="-|>", rad=0.0):
        ax.add_patch(FancyArrowPatch(p, q, arrowstyle="<|-|>" if both else style, mutation_scale=16,
                                     linewidth=1.8, color=color, zorder=1,
                                     connectionstyle=f"arc3,rad={rad}"))

    W, H = 2.9, 1.7
    # Row A: shared classical front end
    ya = 7.7
    xs = [0.3, 3.5, 6.7, 9.9, 13.1]
    box(xs[0], ya, W, H, "Configurable scenario", "JSON inputs, priorities,\nsynthetic interference\n(scenario.py)", BLUE, 1)
    box(xs[1], ya, W, H, "Weighted interference graph", "vertices = nodes,\neffective edge weights\n(graph_generator.py)", BLUE, 2)
    box(xs[2], ya, W, H, "Binary decision variables", "x(i,c) = 1 if node i uses\nchannel c  ->  N*C vars\n(qubo_model.py)", BLUE, 3)
    box(xs[3], ya, W, H, "QUBO construction", "interference + P*(exactly-one)^2\nAutomatic safe penalty P\n(qubo_model.py)", BLUE, 4)
    box(xs[4], ya, W, H, "Ising Hamiltonian", "x = (1 - z)/2  ->  h, J, const\nZ and ZZ Pauli terms\n(qubo_model.py)", BLUE, 5)
    for a, b in zip(xs[:-1], xs[1:]):
        arrow((a + W + 0.04, ya + H / 2), (b - 0.04, ya + H / 2))

    # Row B: baseline (left) and quantum (right)
    yb = 4.05
    box(0.5, yb, 2.7, 1.9, "Classical Solvers", "Exhaustive (exact)\nGreedy (priority-degree)\nSimulated Annealing\n(classical_solver.py)", GREEN, 8)
    box(3.45, yb, 2.6, 1.9, "Classical Solutions", "exact global minimum\n& heuristic allocations\n+ optimality gap analysis", GREEN)
    arrow((3.45 + 0.1, ya - 0.04), (1.85, yb + 1.9 + 0.04), color="#2e7d32", rad=0.0)
    arrow((3.2 + 0.04, yb + 0.95), (3.45 - 0.04, yb + 0.95), color="#2e7d32")

    box(6.7, yb, 2.8, 1.9, "QAOA quantum circuit", "H on all qubits, then p layers:\ncost RZ/RZZ(gamma), mixer RX(beta)\nMemory checks & safe execution\n(quantum_solver.py)", PURPLE, 6)
    box(9.85, yb, 2.8, 1.9, "Measurement + decoding", "8,192 shots -> bitstrings\nqubit 0 = rightmost character\n-> node-channel allocation,\nvalid / invalid split", PURPLE, 7)
    box(13.0, yb, 2.8, 1.9, "Candidate allocations", "QUBO energy per candidate\nbest valid allocation\nfrequency of valid / optimal", PURPLE)
    arrow((14.55, ya - 0.04), (14.55, 6.0 + 0.55), color="#6a3d9a")
    ax.plot([14.55, 8.1], [6.0 + 0.55, 6.0 + 0.55], color="#6a3d9a", lw=1.8, zorder=1)
    arrow((8.1, 6.0 + 0.55), (8.1, yb + 1.9 + 0.04), color="#6a3d9a")
    arrow((9.5 + 0.04, yb + 0.95), (9.85 - 0.04, yb + 0.95), color="#6a3d9a")
    arrow((12.65 + 0.04, yb + 0.95), (13.0 - 0.04, yb + 0.95), color="#6a3d9a")

    # hybrid loop
    box(6.7, 2.1, 2.8, 1.35, "Classical optimizer", "grid search + COBYLA tune\ngamma, beta from sampled energy", BLUE)
    arrow((8.1, yb - 0.04), (8.1, 3.45 + 0.04), both=True, color="#444444")
    ax.text(8.25, 3.77, "parameters  <->  mean energy", fontsize=8, color="#444444", va="center")

    # Row C: random baseline + comparison
    box(9.85, 2.1, 2.8, 1.35, "Random-sampling baseline", "8,192 random bitstrings,\nscored like QAOA output", GREY)
    box(0.5, 0.25, 15.3, 1.5, "9. Results comparison and visualization",
        "exact optimum vs Greedy vs SA vs QAOA vs random sampling: scores, valid rates, gap, runtime\n"
        "topology visualization with channel coloring and clash highlight | JSON export (visualization.py, main.py)", BLUE)
    arrow((4.75, yb - 0.04), (4.75, 1.75 + 0.04), color="#2e7d32")
    arrow((14.4, yb - 0.04), (14.4, 1.75 + 0.04), color="#6a3d9a")
    arrow((11.25, 2.1 - 0.04), (11.25, 1.75 + 0.04), color="#666666")

    # legend
    for i, (c, t) in enumerate([(BLUE, "Classical"), (PURPLE, "Quantum (simulated)"),
                                (GREEN, "Classical Baselines"), (GREY, "Reference baseline")]):
        ax.add_patch(Rectangle((0.3 + i * 3.6, 9.55), 0.3, 0.25, facecolor=c, edgecolor=EDGE[c]))
        ax.text(0.7 + i * 3.6, 9.675, t, va="center", fontsize=9)
    ax.set_title("RescueMesh architecture: configurable quantum-assisted channel allocation vs classical solvers",
                 fontsize=13, fontweight="bold", y=0.985)
    fig.savefig(filename, dpi=170, bbox_inches="tight")
    plt.close(fig)
    return filename
