# RescueMesh

**Quantum-assisted channel allocation for emergency wireless mesh networks**

A Qiskit Fall Fest 2026 project exploring how limited wireless channels can be assigned across emergency mesh nodes using QUBO, Ising Hamiltonians, and QAOA—benchmarked against classical optimization.

> **Scope:** RescueMesh is a software simulation. It uses synthetic interference weights, not measured RF/SINR data or deployed radio hardware. QAOA runs on the classical Qiskit Aer simulator. **No quantum advantage or speedup is claimed.**

## Start here

- **[Project overview and technical documentation](RescueMesh/README.md)** — formulation, architecture, experiments, setup, and limitations.
- **[Demonstration guide](RescueMesh/report/DEMO_GUIDE.md)** — commands and suggested live-demo sequence.
- **[Presentation script and technical Q&A](RescueMesh/report/video_script.md)** — concise walkthrough and anticipated judge questions.
- **[Technical report](RescueMesh/report/RescueMesh_Report.docx)**
- **[Architecture diagram](RescueMesh/report/architecture_diagram.png)**
- **[Scenario definitions](RescueMesh/scenarios/)** — original, unavoidable-interference, realistic 8-node, and dense 12-node cases.
- **[Experiment outputs](RescueMesh/results/)** — plots, CSV comparison, and JSON artifacts.

## What it does

1. Models emergency communication nodes as a weighted interference graph.
2. Builds a QUBO that minimizes same-channel interference while enforcing exactly one channel per node.
3. Converts the QUBO into an Ising Hamiltonian.
4. Runs classical baselines: exhaustive search (when tractable), greedy allocation, and simulated annealing.
5. Runs QAOA with Qiskit Aer when the statevector safety limit allows it.
6. Independently checks QUBO/Ising consistency and evaluates sampled bitstrings.

## Selected experiment: unavoidable-interference case

The 5-node, 3-channel benchmark contains a four-node clique, so at least one same-channel conflict is unavoidable. In the recorded 4,096-shot runs:

| Metric | QAOA p=1 | QAOA p=2 |
|---|---:|---:|
| Valid sampled allocations | 18.14% | 48.46% |
| Optimal sampled allocations | 0.37% | 1.64% |
| Mean sampled QUBO energy | 51.84 | 40.42 |
| Optimization time | 53.4 s | 17.3 s |
| Best valid interference | 2.40 | 2.40 |

The exact classical optimum is **2.40**, with six optimal assignments. On this small instance, exhaustive search, greedy allocation, and simulated annealing also find the optimum in milliseconds. The QAOA figures are individual experimental runs, not statistical evidence of general improvement; p=2's shorter measured optimization time reflects its optimizer evaluation path in this run, not a general rule that deeper circuits run faster.

## Quick start

From the repository root:

```bash
cd RescueMesh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m unittest discover -s tests -v
```

Run the QAOA comparison on the unavoidable-interference scenario:

```bash
python main.py --scenario scenarios/unavoidable_5node.json --p 2 --shots 4096
```

Run the larger 8-node case with classical solvers only:

```bash
python main.py --scenario scenarios/realistic_8node.json --no-qaoa
```

See the [full README](RescueMesh/README.md) for installation details, commands, math, and the project map.

## Repository map

```text
.
├── README.md                    # This landing page
├── LICENSE
└── RescueMesh/                  # Python application root
    ├── main.py                  # CLI entry point
    ├── simulation.py            # End-to-end experiment pipeline
    ├── scenario.py              # Scenario model and validation
    ├── scenario_generator.py    # Synthetic topology generator
    ├── classical_solver.py      # Exact, greedy, simulated annealing
    ├── qubo_model.py            # QUBO and Ising formulation
    ├── quantum_solver.py        # QAOA / Qiskit Aer
    ├── evaluation.py            # Independent validation and metrics
    ├── visualization.py         # Network and result plots
    ├── scenarios/               # JSON benchmark inputs
    ├── tests/                   # Automated tests
    ├── results/                 # Generated and recorded outputs
    └── report/                  # Report and demo materials
```

## Reproducibility and scientific limitations

- The supplied scenarios and link weights are synthetic modeling inputs.
- QAOA is executed using a classical statevector simulator; no QPU run is reported.
- Statevector memory grows exponentially with qubit count. The CLI uses an 18-qubit safety limit by default; larger cases should use classical solvers unless the user deliberately overrides the guard.
- The classical baselines are expected to outperform statevector QAOA on these small instances.
- Runtime and sampling percentages depend on the machine, optimizer path, seed, and shot budget. Treat reported values as recorded runs, not universal performance guarantees.

Developed for **Qiskit Fall Fest 2026**.
