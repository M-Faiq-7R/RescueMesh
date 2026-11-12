"""main.py - RescueMesh entry point: configurable quantum-assisted channel allocation.

Reproduces the exact original experiment by default, or runs custom JSON scenarios,
synthetic scenarios, and classical/quantum benchmark comparisons.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scenario import Scenario
from scenario_generator import generate_synthetic_scenario
from simulation import run_simulation


def parse_args():
    parser = argparse.ArgumentParser(
        description="RescueMesh: Configurable Quantum-Assisted Wireless Channel Allocation Simulation."
    )
    parser.add_argument(
        "--scenario",
        type=str,
        default=None,
        help="Path to JSON scenario file (e.g. scenarios/realistic_8node.json). "
             "If omitted, runs the original 5-node benchmark scenario."
    )
    parser.add_argument(
        "--generate-scenario",
        action="store_true",
        help="Generate and evaluate a synthetic scenario on the fly."
    )
    parser.add_argument(
        "--nodes",
        type=int,
        default=8,
        help="Number of nodes when generating a synthetic scenario (default: 8)."
    )
    parser.add_argument(
        "--channels",
        type=int,
        default=3,
        help="Number of channels when generating a synthetic scenario (default: 3)."
    )
    parser.add_argument(
        "--density",
        type=float,
        default=0.45,
        help="Edge density when generating a synthetic scenario (default: 0.45)."
    )
    parser.add_argument(
        "--p",
        type=int,
        default=2,
        choices=[1, 2],
        help="QAOA circuit layers p (default: 2)."
    )
    parser.add_argument(
        "--shots",
        type=int,
        default=8192,
        help="Number of sampling shots (default: 8192)."
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)."
    )
    parser.add_argument(
        "--no-qaoa",
        dest="run_qaoa",
        action="store_false",
        help="Disable QAOA quantum simulation (run only classical solvers: Exhaustive, Greedy, SA)."
    )
    parser.add_argument(
        "--qaoa",
        dest="run_qaoa",
        action="store_true",
        help="Enable QAOA quantum simulation (enabled by default on instances <= 18 qubits)."
    )
    parser.set_defaults(run_qaoa=True)
    parser.add_argument(
        "--force-qaoa",
        action="store_true",
        help="Force QAOA execution even if qubit count exceeds the state-vector memory safety limit (18 qubits)."
    )
    parser.add_argument(
        "--outdir",
        type=str,
        default="results",
        help="Directory where output plots, JSON files, and tables will be written (default: results)."
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Determine scenario
    if args.generate_scenario:
        print(f"Generating synthetic scenario with {args.nodes} nodes, {args.channels} channels (seed={args.seed})...")
        scenario = generate_synthetic_scenario(
            n_nodes=args.nodes,
            n_channels=args.channels,
            edge_density=args.density,
            seed=args.seed,
            force_unavoidable=True,
        )
    elif args.scenario is not None:
        scenario_path = Path(args.scenario)
        if not scenario_path.exists():
            print(f"Error: Scenario file '{args.scenario}' not found.", file=sys.stderr)
            sys.exit(1)
        scenario = Scenario.from_json(scenario_path)
    else:
        # Default baseline: from config.py
        scenario = Scenario.from_config()

    # Execute simulation
    run_simulation(
        scenario=scenario,
        run_qaoa=args.run_qaoa,
        p_layers=args.p,
        shots=args.shots,
        seed=args.seed,
        max_qaoa_qubits=18,
        force_qaoa=args.force_qaoa,
        outdir=args.outdir,
        verbose=True,
    )


if __name__ == "__main__":
    main()
