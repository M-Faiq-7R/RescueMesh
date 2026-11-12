"""simulation.py - Unified simulation runner for RescueMesh.

Orchestrates:
1. Scenario loading, validation, and graph construction.
2. Classical optimization: Exhaustive, Greedy, and Simulated Annealing.
3. QUBO and Ising Hamiltonian formulation with validation.
4. QAOA quantum circuit simulation with state-vector memory safety.
5. Network visualization with channel coloring and clash highlighting.
6. Structured evaluation, optimality gap analysis, and JSON export.
"""

from __future__ import annotations

import csv
import json
import os
import time
from typing import Any, Dict, List, Optional, Union

import numpy as np

import config
from classical_solver import (compute_optimality_gap, edge_interference,
                              solve_exhaustive, solve_greedy,
                              solve_simulated_annealing, validate_solution)
from evaluation import (method_stats, random_baseline, random_counts,
                        summarize_samples, validate_qubo, verify_results)
from graph_generator import build_interference_graph
from qubo_model import all_bitstrings, build_qubo, decode, qubo_energies, qubo_to_ising
from quantum_solver import (QAOASolver, analyze_counts,
                            check_qaoa_feasibility)
from scenario import Scenario
from visualization import (draw_allocated_network, draw_architecture,
                           draw_network, plot_phase5)


def run_simulation(
    scenario: Optional[Union[Scenario, str]] = None,
    run_qaoa: bool = True,
    p_layers: int = 1,
    shots: int = 8192,
    seed: int = 42,
    max_qaoa_qubits: int = 18,
    force_qaoa: bool = False,
    outdir: str = "results",
    verbose: bool = True,
) -> Dict[str, Any]:
    """Execute complete RescueMesh simulation pipeline for a scenario.

    Parameters:
        scenario: Scenario object, path to JSON scenario file, or None (defaults to config.py).
        run_qaoa: Whether to attempt QAOA execution.
        p_layers: QAOA circuit depth layers (1 or 2).
        shots: Sampling shot budget for stochastic methods.
        seed: Random seed for 100% reproducible execution.
        max_qaoa_qubits: Maximum qubit limit for statevector simulator.
        force_qaoa: Override max_qaoa_qubits safety check.
        outdir: Directory to save generated artifacts and figures.
        verbose: Whether to print progress to stdout.

    Returns:
        Structured results dictionary.
    """
    os.makedirs(outdir, exist_ok=True)

    # 1. Load Scenario
    if scenario is None:
        sc = Scenario.from_config()
    elif isinstance(scenario, str):
        sc = Scenario.from_json(scenario)
    else:
        sc = scenario

    if verbose:
        print("=" * 70)
        print(f"RescueMesh Simulation: {sc.name}")
        print("=" * 70)
        print(f"Description: {sc.description}")
        print(f"Nodes ({len(sc.nodes)}): {sc.nodes}")
        print(f"Channels ({len(sc.channels)}): {sc.channels}")
        print(f"Edges: {len(sc.edges)} links | Safe Penalty P: {sc.penalty:.1f}")
        print(f"Disclaimer: {sc.to_dict()['disclaimer']}")

    # 2. Build Interference Graph
    graph = build_interference_graph(scenario=sc)
    raw_plot = f"{outdir}/network_graph.png"
    draw_network(graph, filename=raw_plot)
    if verbose:
        print(f"Saved initial topology visualization to {raw_plot}")

    # 3. Classical Solvers
    if verbose:
        print("\n--- Classical Optimization Baselines ---")

    # 3a. Exhaustive Search (if manageable)
    t0 = time.perf_counter()
    exhaustive_res = solve_exhaustive(graph, nodes=sc.nodes, channels=sc.channels, max_combinations=500_000)
    t_exhaustive = time.perf_counter() - t0

    exact_best = exhaustive_res["best_score"]
    if not exhaustive_res.get("skipped", False):
        if verbose:
            print(f"[Exhaustive Search] Evaluated {len(exhaustive_res['all_scores'])} assignments in {t_exhaustive*1000:.1f} ms")
            print(f"  Exact Global Minimum Interference: {exact_best:g}")
            print(f"  Number of Global Optima: {len(exhaustive_res['all_optimal'])}")
            print(f"  One Optimal Assignment: {exhaustive_res['best_assignment']}")
        checks = validate_solution(graph, exhaustive_res, nodes=sc.nodes, channels=sc.channels)
        for name, passed in checks:
            if verbose:
                print(f"    [{'PASS' if passed else 'FAIL'}] {name}")
            assert passed, f"Exhaustive validation check failed: {name}"
    else:
        if verbose:
            print(f"[Exhaustive Search] {exhaustive_res['reason']}")

    # 3b. Greedy Solver
    greedy_res = solve_greedy(graph, nodes=sc.nodes, channels=sc.channels, seed=seed, order_strategy="priority_degree")
    greedy_gap = compute_optimality_gap(greedy_res["best_score"], exact_best)
    if verbose:
        print(f"[Greedy Solver] Score: {greedy_res['best_score']:g} | Runtime: {greedy_res['runtime_seconds']*1000:.2f} ms | Gap: {greedy_gap['gap_str']}")
        print(f"  Assignment: {greedy_res['best_assignment']}")

    # 3c. Simulated Annealing
    sa_res = solve_simulated_annealing(
        graph, nodes=sc.nodes, channels=sc.channels, initial_temp=15.0,
        cooling_rate=0.995, max_steps=8000, seed=seed
    )
    sa_gap = compute_optimality_gap(sa_res["best_score"], exact_best)
    if verbose:
        print(f"[Simulated Annealing] Score: {sa_res['best_score']:g} | Runtime: {sa_res['runtime_seconds']*1000:.2f} ms | Gap: {sa_gap['gap_str']}")
        print(f"  Assignment: {sa_res['best_assignment']}")

    # 4. QUBO and Ising Formulation
    if verbose:
        print(f"\n--- QUBO & Ising Model (Penalty P = {sc.penalty:.1f}) ---")
    Q, offset = build_qubo(graph, nodes=sc.nodes, channels=sc.channels, penalty=sc.penalty)
    h, J, const = qubo_to_ising(Q, offset)
    if verbose:
        print(f"QUBO variables: {Q.shape[0]}, Non-zero Q entries: {int((Q != 0).sum())}, Offset: {offset:.1f}")
        print(f"Ising terms: {len(h)} single-Z, {len(J)} ZZ couplers, const = {const:.2f}")

    qubo_checks = validate_qubo(graph, Q, offset, exhaustive_res, nodes=sc.nodes, channels=sc.channels, penalty=sc.penalty)
    for name, passed, detail in qubo_checks:
        if verbose:
            print(f"  [{'PASS' if passed else 'FAIL'}] {name} ({detail})")
        assert passed, f"QUBO validation check failed: {name}"

    # 5. Quantum Optimization (QAOA)
    n_qubits = len(sc.nodes) * len(sc.channels)
    feasible, feas_msg, mem_mb = check_qaoa_feasibility(len(sc.nodes), len(sc.channels), max_qubits=max_qaoa_qubits)

    qaoa_executed = False
    methods_dict: Dict[str, Any] = {}
    runtimes_dict: Dict[str, float] = {
        "exhaustive": t_exhaustive if not exhaustive_res.get("skipped", False) else 0.0,
        "greedy": greedy_res["runtime_seconds"],
        "simulated_annealing": sa_res["runtime_seconds"],
    }

    if run_qaoa and (feasible or force_qaoa):
        if verbose:
            print(f"\n--- QAOA Execution (Qiskit Aer State-Vector Simulator) ---")
            print(f"Allocating {n_qubits} qubits (estimated statevector RAM: {mem_mb:.2f} MB)")

        qaoa_executed = True
        # QAOA p=1
        solver1 = QAOASolver(Q, offset, h, J, const, p=1, shots=4096, seed=seed)
        if verbose:
            print(f"Circuit compiled: {solver1.compiled.num_qubits} qubits, depth {solver1.compiled.depth()}, "
                  f"gates: {dict(solver1.compiled.count_ops())}")
            print("Optimizing (gamma, beta) with coarse grid + COBYLA...")

        t0 = time.perf_counter()
        params1, mean_e1 = solver1.optimize()
        t_opt_p1 = time.perf_counter() - t0

        t0 = time.perf_counter()
        counts1 = solver1.sample(params1, shots=shots)
        t_sample_p1 = time.perf_counter() - t0
        rows1 = analyze_counts(counts1, solver1.table, nodes=sc.nodes, channels=sc.channels)
        qaoa1_summary = summarize_samples(rows1, graph, exact_best)

        # Random baseline for comparison
        t0 = time.perf_counter()
        rand_counts = random_counts(n_qubits, shots, seed=seed)
        t_sample_rand = time.perf_counter() - t0
        rand_rows = analyze_counts(rand_counts, solver1.table, nodes=sc.nodes, channels=sc.channels)
        rand_summary = summarize_samples(rand_rows, graph, exact_best)

        methods_dict["Random sampling"] = dict(method_stats(rand_rows, exact_best), counts=rand_counts)
        methods_dict["QAOA p=1"] = dict(
            method_stats(rows1, exact_best), counts=counts1,
            parameters={"gamma": [float(params1[0])], "beta": [float(params1[1])]},
            optimization={"evaluations": solver1.n_evaluations, "shots_per_evaluation": 4096,
                          "final_sampled_mean_energy": float(mean_e1)}
        )
        runtimes_dict["random_sampling"] = t_sample_rand
        runtimes_dict["qaoa_p1_optimization"] = t_opt_p1
        runtimes_dict["qaoa_p1_sampling"] = t_sample_p1

        if verbose:
            print(f"QAOA p=1: {solver1.n_evaluations} evaluations in {t_opt_p1:.1f} s | Best mean energy: {mean_e1:.2f}")
            print(f"  Valid solution rate: {methods_dict['QAOA p=1']['valid_pct']:.2f}% (Random: {methods_dict['Random sampling']['valid_pct']:.2f}%)")
            opt_pct = methods_dict['QAOA p=1']['optimal_pct']
            print(f"  Optimal solution rate: {opt_pct:.2f}% (Random: {methods_dict['Random sampling']['optimal_pct']:.2f}%)")
            print(f"  Best valid score: {methods_dict['QAOA p=1']['best_valid_score']} (Exact best: {exact_best})")

        # Optional QAOA p=2
        if p_layers >= 2:
            if verbose:
                print("\nExecuting QAOA p=2 with multi-start COBYLA refinement...")
            g1, b1 = float(params1[0]), float(params1[1])
            rng = np.random.default_rng(seed)
            starts = [
                [g1, 0.0, b1, 0.0],
                [g1, g1, b1, b1]
            ]
            starts += [
                [rng.uniform(0, 0.3), rng.uniform(0, 0.3), rng.uniform(0, np.pi), rng.uniform(0, np.pi)]
                for _ in range(6)
            ]
            solver2 = QAOASolver(Q, offset, h, J, const, p=2, shots=4096, seed=seed)
            t0 = time.perf_counter()
            params2, mean_e2 = solver2.optimize_from_starts(starts)
            t_opt_p2 = time.perf_counter() - t0

            t0 = time.perf_counter()
            counts2 = solver2.sample(params2, shots=shots)
            t_sample_p2 = time.perf_counter() - t0
            rows2 = analyze_counts(counts2, solver2.table, nodes=sc.nodes, channels=sc.channels)

            methods_dict["QAOA p=2"] = dict(
                method_stats(rows2, exact_best), counts=counts2,
                parameters={"gamma": params2[:2].tolist(), "beta": params2[2:].tolist()},
                optimization={"evaluations": solver2.n_evaluations, "shots_per_evaluation": 4096,
                              "final_sampled_mean_energy": float(mean_e2)}
            )
            runtimes_dict["qaoa_p2_optimization"] = t_opt_p2
            runtimes_dict["qaoa_p2_sampling"] = t_sample_p2
            if verbose:
                print(f"QAOA p=2: {solver2.n_evaluations} evaluations in {t_opt_p2:.1f} s | Best mean energy: {mean_e2:.2f}")
                print(f"  Valid solution rate: {methods_dict['QAOA p=2']['valid_pct']:.2f}% | Optimal rate: {methods_dict['QAOA p=2']['optimal_pct']:.2f}%")

        # Save qaoa_results.json
        qaoa_export = {
            "p": p_layers, "shots": shots, "seed": seed,
            "gamma": float(params1[0]), "beta": float(params1[1]),
            "counts": counts1,
            "summary": {k: v for k, v in qaoa1_summary.items() if k != "best_valid"},
            "random_baseline": {k: v for k, v in rand_summary.items() if k != "best_valid"}
        }
        with open(f"{outdir}/qaoa_results.json", "w", encoding="utf-8") as f:
            json.dump(qaoa_export, f, indent=2)

    else:
        if verbose:
            print("\n--- Quantum Optimization (QAOA) ---")
            if not run_qaoa:
                print("QAOA execution disabled (--no-qaoa).")
            else:
                print(f"QAOA skipped: {feas_msg}")

    # 6. Best Allocation Visualization (Channel coloring & Clash highlighting)
    # Choose best overall solution to visualize
    candidate_solutions = [
        ("Greedy", greedy_res["best_assignment"], greedy_res["best_score"]),
        ("Simulated Annealing", sa_res["best_assignment"], sa_res["best_score"]),
    ]
    if not exhaustive_res.get("skipped", False):
        candidate_solutions.insert(0, ("Exhaustive", exhaustive_res["best_assignment"], exhaustive_res["best_score"]))
    if qaoa_executed and methods_dict.get("QAOA p=1", {}).get("best_valid_score") is not None:
        best_qaoa_row = min((r for r in rows1 if r["valid"]), key=lambda r: r["energy"])
        candidate_solutions.append(("QAOA p=1", best_qaoa_row["assignment"], best_qaoa_row["energy"]))

    # Sort candidates by score
    candidate_solutions.sort(key=lambda item: item[2])
    best_solver_name, best_overall_assignment, best_overall_score = candidate_solutions[0]

    alloc_plot = f"{outdir}/allocated_network.png"
    draw_allocated_network(
        graph, best_overall_assignment, filename=alloc_plot,
        title=f"RescueMesh: Best Channel Allocation ({best_solver_name}, cost={best_overall_score:g})",
        seed=seed
    )
    if verbose:
        print(f"\nSaved channel-allocated network visualization to {alloc_plot}")
        print(f"Allocated solution ({best_solver_name}): {best_overall_assignment}")

    # 7. Compile Results Dictionary
    all_valid_scores = [s for _, s in exhaustive_res["all_scores"]] if not exhaustive_res.get("skipped", False) else []
    results = {
        "scenario": sc.to_dict(),
        "config": {
            "nodes": sc.nodes,
            "channels": sc.channels,
            "edges": sc.edges,
            "penalty": sc.penalty,
            "shots": shots,
            "seed": seed,
            "qaoa_executed": qaoa_executed,
            "optimization_shots_per_evaluation": 4096 if qaoa_executed else 0,
        },
        "exact": {
            "skipped": exhaustive_res.get("skipped", False),
            "best_score": exact_best,
            "n_assignments": len(all_valid_scores),
            "n_optimal_assignments": len(exhaustive_res["all_optimal"]),
            "mean_interference_over_valid": (sum(all_valid_scores) / len(all_valid_scores)) if all_valid_scores else None,
            "best_assignment": exhaustive_res["best_assignment"],
        },
        "classical": {
            "greedy": {
                "best_score": greedy_res["best_score"],
                "assignment": greedy_res["best_assignment"],
                "gap": greedy_gap,
                "runtime_seconds": greedy_res["runtime_seconds"],
            },
            "simulated_annealing": {
                "best_score": sa_res["best_score"],
                "assignment": sa_res["best_assignment"],
                "gap": sa_gap,
                "runtime_seconds": sa_res["runtime_seconds"],
            },
        },
        "methods": methods_dict,
        "runtime_seconds": runtimes_dict,
        "best_overall": {
            "method": best_solver_name,
            "score": best_overall_score,
            "assignment": best_overall_assignment,
        },
    }

    # Save results JSON
    with open(f"{outdir}/experiment_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    # If running original 5-node scenario with QAOA, also save phase5_results.json for backward compatibility
    if qaoa_executed:
        with open(f"{outdir}/phase5_results.json", "w", encoding="utf-8") as f:
            json.dump(results, f, indent=1)

        # Generate Phase 5 figures
        plot_phase5(results, outdir=outdir)
        draw_architecture(f"report/architecture_diagram.png")

        # Independent verification
        checks5 = verify_results(results, graph, nodes=sc.nodes, channels=sc.channels, penalty=sc.penalty)
        if verbose:
            print("\nIndependent verification from raw bitstrings:")
            for name, passed, detail in checks5:
                print(f"  [{'PASS' if passed else 'FAIL'}] {name} ({detail})")
                assert passed, f"Verification failed: {name}"

    # Print summary table
    if verbose:
        print("\n" + "=" * 90)
        print("OPTIMIZATION PERFORMANCE SUMMARY")
        print("=" * 90)
        table_rows = [
            ["Algorithm", "Type", "Best Score", "Opt Gap", "Runtime"]
        ]
        if not exhaustive_res.get("skipped", False):
            table_rows.append(["Exhaustive Search", "Exact Classical", f"{exact_best:g}", "0.00 (optimal)", f"{t_exhaustive*1000:.1f} ms"])
        table_rows.append(["Greedy Allocation", "Heuristic Classical", f"{greedy_res['best_score']:g}", greedy_gap["gap_str"], f"{greedy_res['runtime_seconds']*1000:.2f} ms"])
        table_rows.append(["Simulated Annealing", "Metaheuristic", f"{sa_res['best_score']:g}", sa_gap["gap_str"], f"{sa_res['runtime_seconds']*1000:.2f} ms"])
        if qaoa_executed:
            m1 = methods_dict["QAOA p=1"]
            gap1 = compute_optimality_gap(m1["best_valid_score"], exact_best)
            table_rows.append(["QAOA p=1", "Simulated Quantum", f"{m1['best_valid_score']:g}", gap1["gap_str"], f"{runtimes_dict['qaoa_p1_optimization']:.1f}s opt + {runtimes_dict['qaoa_p1_sampling']:.2f}s"])
            if "QAOA p=2" in methods_dict:
                m2 = methods_dict["QAOA p=2"]
                gap2 = compute_optimality_gap(m2["best_valid_score"], exact_best)
                table_rows.append(["QAOA p=2", "Simulated Quantum", f"{m2['best_valid_score']:g}", gap2["gap_str"], f"{runtimes_dict['qaoa_p2_optimization']:.1f}s opt + {runtimes_dict['qaoa_p2_sampling']:.2f}s"])
            mr = methods_dict["Random sampling"]
            gap_r = compute_optimality_gap(mr["best_valid_score"], exact_best)
            table_rows.append(["Random Sampling", "Unoptimized Guess", f"{mr['best_valid_score']:g}", gap_r["gap_str"], f"{runtimes_dict['random_sampling']:.2f} s"])

        col_widths = [max(len(row[i]) for row in table_rows) for i in range(len(table_rows[0]))]
        for idx, row in enumerate(table_rows):
            line = "  " + " | ".join(cell.ljust(col_widths[i]) for i, cell in enumerate(row))
            print(line)
            if idx == 0:
                print("  " + "-+-".join("-" * col_widths[i] for i in range(len(col_widths))))

        # Save CSV comparison
        with open(f"{outdir}/comparison_table.csv", "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(table_rows)

        print("\nAll artifacts successfully saved to:", os.path.abspath(outdir))

    return results
