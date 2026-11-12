# RescueMesh — Technical Documentation

**Quantum-assisted channel allocation for emergency wireless mesh networks**

RescueMesh is a configurable simulation framework for studying channel allocation in post-disaster emergency wireless mesh networks. It formulates weighted same-channel interference as a QUBO, maps the model to an Ising Hamiltonian, and evaluates QAOA using Qiskit Aer alongside classical baselines.

> **Scientific scope:** This repository does not deploy radios or measure real RF interference. Scenario edge weights and node priorities are synthetic modeling inputs. QAOA is simulated on a classical computer. No quantum advantage or speedup is claimed.

## Contents

- [Problem and workflow](#problem-and-workflow)
- [Mathematical model](#mathematical-model)
- [Algorithms](#algorithms)
- [Scenarios](#scenarios)
- [Recorded QAOA experiment](#recorded-qaoa-experiment)
- [Installation](#installation)
- [Run commands](#run-commands)
- [Tests](#tests)
- [Outputs](#outputs)
- [Project map](#project-map)
- [Limitations](#limitations)
- [References](#references)

## Problem and workflow

After a disaster, cellular infrastructure may be unavailable. Emergency response teams can deploy portable mesh nodes for command, medical, rescue, shelter, and logistics functions. Nodes that interfere with one another should avoid using the same channel where possible.

The pipeline is:

1. Load and validate a JSON scenario.
2. Build an undirected weighted interference graph.
3. Compute priority-adjusted edge weights.
4. Solve with exhaustive search (when tractable), greedy allocation, and simulated annealing.
5. Construct and validate the QUBO and equivalent Ising model.
6. Run QAOA on Qiskit Aer when the qubit safety guard permits.
7. Decode measured bitstrings, verify assignments, and export tables, JSON, and plots.

## Mathematical model

Let (x_{i,c}\in\{0,1\}) indicate whether node (i) is assigned channel (c). Each node must receive exactly one channel.

The effective edge weight is:

[
w_{uv}^{\mathrm{eff}} = w_{uv}(p_u p_v)
]

where (w_{uv}) is the scenario's synthetic edge weight and (p_u,p_v) are node priorities.

The QUBO objective is:

[
E(x)=
\sum_{(u,v)\in\mathcal E}w_{uv}^{\mathrm{eff}}
\sum_{c\in\mathcal C}x_{u,c}x_{v,c}
+
P\sum_{i\in\mathcal V}
\left(\sum_{c\in\mathcal C}x_{i,c}-1\right)^2
]

The first term penalizes adjacent nodes assigned the same channel. The second penalizes assignments that do not select exactly one channel per node. The scenario model validates supplied data and computes a safe penalty when one is not provided.

The binary-to-spin substitution is:

[
x_i=\frac{1-Z_i}{2}
]

This produces an Ising cost Hamiltonian with constant, single-(Z), and pairwise-(ZZ) terms. The QAOA cost layer uses the corresponding (R_Z) and (R_{ZZ}) rotations; the mixer uses (R_X) rotations.

## Algorithms

| Method | Purpose |
|---|---|
| Exhaustive search | Exact global optimum and all optimal assignments for manageable (C^N) search spaces. |
| Greedy allocation | Fast valid assignment using priority/degree ordering. |
| Simulated annealing | Classical metaheuristic that explores valid channel assignments. |
| QAOA | Variational quantum algorithm simulated by Qiskit Aer; parameter optimization is classical. |
| Random sampling | Unoptimized baseline for comparing feasibility and optimal-sample rates. |

The default QAOA safety threshold is 18 qubits. A statevector stores (2^n) complex amplitudes (16 bytes each): 15 qubits require 0.5 MiB, 18 require 4 MiB, and 24 require 256 MiB, before simulator and optimization overhead. Use `--no-qaoa` for larger instances unless you understand the memory/runtime implications.

## Scenarios

| File | Description |
|---|---|
| `scenarios/original_5node.json` | Original 5-node, 3-channel benchmark; interference can be eliminated. |
| `scenarios/unavoidable_5node.json` | 5 nodes, 3 channels, and a (K_4) subgraph; unavoidable interference, exact optimum 2.40. |
| `scenarios/realistic_8node.json` | 8-node, 3-channel emergency mesh; exact optimum 15.84 in the recorded exhaustive run. QAOA is skipped by the 18-qubit guard. |
| `scenarios/dense_12node.json` | Dense 12-node, 4-channel case; exhaustive enumeration is large, so use classical heuristics. |

All scenarios are synthetic. The labels describe modeled emergency roles, not actual field deployments.

## Recorded QAOA experiment

The following results are from the recorded 4,096-shot runs on `unavoidable_5node.json`. The exact classical optimum is 2.40, with six optimal assignments.

| Metric | QAOA p=1 | QAOA p=2 |
|---|---:|---:|
| Valid sampled allocations | 18.14% | 48.46% |
| Optimal sampled allocations | 0.37% | 1.64% |
| Mean sampled QUBO energy | 51.84 | 40.42 |
| Optimizer evaluations | 2,643 | 746 |
| Optimization time | 53.4 s | 17.3 s |
| Best valid interference | 2.40 | 2.40 |

The corresponding random baseline had a 0.73% valid rate and a 0.02% optimal rate. The p=2 run improved the observed valid and optimal sampling rates for this instance. This is a single experimental comparison, not a statistical claim.

**Interpretation matters:** mean QUBO energy includes the one-hot constraint penalty, while best valid interference is measured only on valid channel assignments. The classical solvers found the same exact optimum in milliseconds in the recorded run. These experiments therefore demonstrate a working QAOA formulation and sampling pipeline—not a practical runtime advantage over classical optimization.

## Installation

Tested with Python 3.12 and the pinned dependencies in `requirements.txt`.

From the repository root:

```bash
cd RescueMesh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

On Windows PowerShell, activate with:

```powershell
.venv\Scripts\Activate.ps1
```

## Run commands

Run the default original benchmark:

```bash
python main.py
```

Run the unavoidable-interference scenario with QAOA p=1:

```bash
python main.py --scenario scenarios/unavoidable_5node.json --p 1 --shots 4096
```

Run p=1 and p=2 comparison:

```bash
python main.py --scenario scenarios/unavoidable_5node.json --p 2 --shots 4096
```

Run the 8-node scenario without QAOA:

```bash
python main.py --scenario scenarios/realistic_8node.json --no-qaoa
```

Generate a synthetic scenario (the CLI's generator mode):

```bash
python main.py --generate-scenario --nodes 8 --channels 3 --density 0.45 --seed 42
```

Choose a different output directory:

```bash
python main.py --scenario scenarios/unavoidable_5node.json --no-qaoa --outdir results/custom_run
```

See `python main.py --help` for all options.

## Tests

Run the automated suite:

```bash
python -m unittest discover -s tests -v
```

The maintained test suite covers scenario validation, deterministic synthetic generation, classical solvers, optimality gaps, QUBO/Ising energy equivalence, quantum helper and memory checks, and visualization. The latest recorded local verification was **25 tests passed**. Re-run the suite after changes in your environment.

## Outputs

The simulation writes to the selected output directory (default: `results/`), including:

- `network_graph.png` — weighted network topology.
- `allocated_network.png` — channel-colored allocation with same-channel conflicts highlighted.
- `experiment_results.json` — structured scenario, solver, and validation results.
- `comparison_table.csv` — compact method comparison.
- Additional QAOA and experiment JSON artifacts, depending on the run.

The repository also includes saved benchmark plots and JSON outputs. These are recorded artifacts, not automatically regenerated by reading the README.

## Project map

```text
RescueMesh/
├── main.py                  # CLI and argument parsing
├── simulation.py            # End-to-end simulation orchestration
├── scenario.py              # Scenario data model and validation
├── scenario_generator.py    # Reproducible synthetic scenario generation
├── graph_generator.py       # Interference graph construction
├── classical_solver.py      # Exhaustive, greedy, simulated annealing
├── qubo_model.py            # QUBO construction and Ising conversion
├── quantum_solver.py        # QAOA circuit and Aer execution
├── evaluation.py            # Mathematical checks and result analysis
├── visualization.py         # Topology and allocation plots
├── config.py                # Original baseline configuration
├── requirements.txt         # Pinned Python dependencies
├── scenarios/               # JSON scenario inputs
├── tests/                   # Automated unit tests
├── results/                 # Saved/generated result artifacts
└── report/
    ├── README.md            # Documentation index
    ├── DEMO_GUIDE.md        # Reproducible demo steps
    ├── video_script.md      # Presentation script and Q&A
    ├── RescueMesh_Report.docx
    └── architecture_diagram.png
```

## Limitations

- Interference weights and priorities are synthetic, not measured RF data.
- No SINR, RSSI, propagation, fading, mobility, or physical-layer simulation is performed.
- QAOA runs on a classical simulator, not quantum hardware.
- Statevector simulation scales exponentially with qubit count.
- Classical exact/heuristic solvers are substantially faster on the tested small cases.
- Reported QAOA percentages and runtimes are run-specific; repeated seeds and statistical analysis would be needed for stronger conclusions.

## References

1. E. Farhi, J. Goldstone, and S. Gutmann, “A Quantum Approximate Optimization Algorithm” (2014), [arXiv:1411.4028](https://arxiv.org/abs/1411.4028).
2. A. Lucas, “Ising Formulations of Many NP Problems,” *Frontiers in Physics* 2, 5 (2014), [doi:10.3389/fphy.2014.00005](https://doi.org/10.3389/fphy.2014.00005).
3. A. Javadi-Abhari et al., “Quantum computing with Qiskit” (2024), [arXiv:2405.08810](https://arxiv.org/abs/2405.08810).
4. [Qiskit Aer](https://github.com/Qiskit/qiskit-aer).

---
Developed for **Qiskit Fall Fest 2026**.
