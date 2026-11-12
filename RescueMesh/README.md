# RescueMesh: Configurable Quantum-Assisted Channel Allocation Simulation

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![Qiskit 2.6](https://img.shields.io/badge/qiskit-2.6.2-purple.svg)](https://qiskit.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**RescueMesh** simulates wireless channel allocation for post-disaster emergency mesh communications using Quadratic Unconstrained Binary Optimization (QUBO), Ising Hamiltonians, and the Quantum Approximate Optimization Algorithm (QAOA) via Qiskit Aer, evaluated alongside classical heuristics (Greedy allocation, Simulated Annealing, and Exhaustive Search).

> [!IMPORTANT]
> **Scientific Integrity & Limitations Summary**
> * **No Quantum Advantage or Speedup**: Classical exact search and classical heuristics (Greedy, Simulated Annealing) vastly outperform simulated QAOA in both solution quality and execution time (milliseconds vs minutes). No quantum advantage or speedup is claimed or demonstrated.
> * **Simulation, Not Real RF Hardware**: All interference link weights and node roles are synthetic modeling heuristics for optimization simulations. They do not represent empirical radio frequency (RF) measurements, signal-to-interference-plus-noise ratio (SINR), RSSI, or hardware physical layer tests.
> * **State-Vector Memory Scaling ($O(2^n)$)**: Idealized state-vector quantum simulators store $2^n$ complex128 amplitudes ($16 \times 2^n$ bytes). For $n \le 18$ qubits, simulation requires $\le 4.2\text{ MB}$; at $n = 24$ qubits (e.g. 8 nodes $\times$ 3 channels), each statevector requires $268\text{ MB}$ and parameter optimization becomes slow. Instances exceeding 18 qubits are safely handled by classical solvers.

---

## Architecture

RescueMesh implements a modular, hybrid classical-quantum evaluation pipeline:

```
+---------------------------------------------------------------------------------------+
| 1. Configurable Network Input (JSON Scenario / Synthetic Generator)                   |
|    - Nodes, channels, synthetic interference edges, node operational priorities       |
|    - Schema validation, duplicate undirected edge rejection, self-loop rejection      |
+---------------------------------------------------------------------------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------------+
| 2. Weighted Interference Graph & Formulation                                          |
|    - Effective weights: w_eff = w * priority_factor(p_u, p_v)                         |
|    - Binary variables: x(i, c) = 1 if node i is assigned channel c                    |
|    - QUBO: E(x) = Interference + P * (Sum_c x(i,c) - 1)^2 with safe penalty P         |
|    - Ising Hamiltonian: x = (1 - z)/2 -> H_C = const + Sum h_i Z_i + Sum J_ij Z_i Z_j |
+---------------------------------------------------------------------------------------+
                   |                                           |
                   v                                           v
+------------------------------------+     +--------------------------------------------+
| 3. Classical Optimization          |     | 4. Quantum Optimization (QAOA)             |
|    - Exhaustive Search (exact)     |     |    - Memory safety check (<18 qubits)      |
|    - Priority-Degree Greedy        |     |    - Equal superposition state |+>^n       |
|    - Simulated Annealing           |     |    - Cost layer RZ/RZZ(gamma)                  |
|    - Optimality gap reporting      |     |    - Mixer layer RX(beta)                      |
|                                    |     |    - COBYLA parameter optimization         |
|                                    |     |    - Shot measurement & bitstring decode   |
+------------------------------------+     +--------------------------------------------+
                   \                                           /
                    \                                         /
                     v                                       v
+---------------------------------------------------------------------------------------+
| 5. Evaluation, Verification & Visualization                                           |
|    - Direct mathematical verification from raw counts & formula                       |
|    - Channel-colored topology plot with bold crimson clash highlighting               |
|    - Performance comparison table & JSON artifact export                              |
+---------------------------------------------------------------------------------------+
```

---

## Scenario Input Format (JSON)

RescueMesh accepts structured JSON scenario files with full schema validation.

### JSON Schema Specification
```json
{
  "name": "Scenario Title (string)",
  "description": "Operational context (string)",
  "is_synthetic": true,
  "rf_measurement": false,
  "nodes": ["A", "B", "C", "D"],
  "channels": [0, 1, 2],
  "edges": [
    ["A", "B", 4.0],
    ["A", "C", 3.0],
    ["B", "C", 5.0]
  ],
  "node_roles": {
    "A": "Command Post",
    "B": "Triage Center",
    "C": "Rescue Team",
    "D": "Shelter"
  },
  "node_priorities": {
    "A": 2.5,
    "B": 2.0,
    "C": 1.5,
    "D": 1.0
  },
  "priority_mode": "product",
  "penalty": 25.0
}
```

### Validation Guarantees
The loader (`scenario.py`) validates:
1. **No duplicate or malformed nodes / channels**.
2. **Endpoint validity**: All edge endpoints must belong to `nodes`.
3. **No self-loops**: Edges like `("A", "A", 2.0)` are rejected.
4. **Undirected edge uniqueness**: If `("A", "B")` exists, any duplicate `("A", "B")` or reversed `("B", "A")` is strictly rejected.
5. **Positive weights & priorities**: All link penalties and node priorities must be positive finite numbers.
6. **Automatic safe penalty computation**: If `penalty` is omitted, $P$ is automatically computed such that $P > \max_u \sum_v w_{uv}^{\text{eff}}$, guaranteeing that no constraint violation can ever beat a valid assignment.

### Provided Scenarios
* [`scenarios/original_5node.json`](file:///home/rajpoot/Desktop/Projects/RescueMesh/RescueMesh/scenarios/original_5node.json): The original benchmark (5 nodes, 3 channels, 3-colorable with global optimum 0.0).
* [`scenarios/unavoidable_5node.json`](file:///home/rajpoot/Desktop/Projects/RescueMesh/RescueMesh/scenarios/unavoidable_5node.json): 5-node scenario containing a 4-clique ($K_4$) with 3 channels. By the Pigeonhole Principle, chromatic number is 4, forcing **unavoidable interference** (exact global optimum = 2.4).
* [`scenarios/realistic_8node.json`](file:///home/rajpoot/Desktop/Projects/RescueMesh/RescueMesh/scenarios/realistic_8node.json): 8-node tactical post-disaster mesh with command posts, field hospitals, triage teams, and shelters. Contains an unavoidable high-density core ($3^8 = 6,561$ exhaustive states, exact global optimum = 15.84).
* [`scenarios/dense_12node.json`](file:///home/rajpoot/Desktop/Projects/RescueMesh/RescueMesh/scenarios/dense_12node.json): 12-node 4-channel dense mesh ($4^{12} \approx 16.7$ million states) where classical heuristics (Greedy and Simulated Annealing) solve the instance in milliseconds.

---

## Mathematical Formulation

For $N$ nodes and $C$ channels, binary decision variables are:
$$x(i, c) = \begin{cases} 1 & \text{if node } i \text{ is assigned channel } c \\ 0 & \text{otherwise} \end{cases}$$

### Objective Function (QUBO)
$$\min_{x \in \{0, 1\}^{N \times C}} E(x) = \sum_{(u, v) \in \mathcal{E}} w_{uv}^{\text{eff}} \sum_{c=0}^{C-1} x(u, c) x(v, c) + P \sum_{i \in \mathcal{V}} \left( \sum_{c=0}^{C-1} x(i, c) - 1 \right)^2$$

Where the priority-weighted effective weight $w_{uv}^{\text{eff}}$ is defined by:
$$w_{uv}^{\text{eff}} = w_{uv} \times (p_u \cdot p_v)$$

Using the idempotent identity $x^2 = x$ for $x \in \{0, 1\}$, each node's constraint expands into:
$$P \left( 1 - \sum_{c=0}^{C-1} x(i, c) + 2 \sum_{0 \le c < c' < C} x(i, c) x(i, c') \right)$$

### Ising Transformation
Substituting $x_i = \frac{1 - z_i}{2}$ with Pauli spin operators $z_i \in \{-1, +1\}$ yields the Ising Hamiltonian:
$$H_C = \text{const} \cdot I + \sum_{i} h_i Z_i + \sum_{i < j} J_{ij} Z_i Z_j$$
where:
$$J_{ij} = \frac{Q_{ij}}{4}, \quad h_i = -\frac{Q_{ii}}{2} - \frac{1}{4} \sum_{j \ne i} Q_{ij}, \quad \text{const} = \text{offset} + \sum_i \frac{Q_{ii}}{2} + \sum_{i < j} \frac{Q_{ij}}{4}$$

---

## Solvers & Algorithms

| Solver | Paradigm | Characteristics |
|---|---|---|
| **Exhaustive Search** | Exact Classical | Evaluates all $C^N$ assignments. Guaranteed global optimum and reports all degenerate minima. Guarded against state spaces $> 500,000$. |
| **Greedy Allocation** | Heuristic Classical | Nodes are sorted by operational priority descending and weighted degree descending; each node greedily selects the channel minimizing incremental clash cost. Execution in $< 1\text{ ms}$. |
| **Simulated Annealing** | Metaheuristic Classical | Maintains strictly valid $\{node: channel\}$ states throughout. Proposes random single-node channel flips with Metropolis acceptance criterion and geometric cooling $T \leftarrow T \times \alpha$. |
| **QAOA ($p=1, 2$)** | Quantum Variational (Simulated) | Alternates cost phase rotations $e^{-i \gamma H_C}$ and mixer rotations $e^{-i \beta \sum X_i}$. Classical optimizer (grid search + COBYLA) tunes $(\gamma, \beta)$ against sampled mean energy. |

---

## Experimental Benchmark Results

### 1. Realistic 8-Node Disaster Response Scenario (`scenarios/realistic_8node.json`)
* Nodes: 8, Channels: 3, Edges: 15, Penalty $P = 50.0$.
* Total valid states: $3^8 = 6,561$.
* **Unavoidable interference**: Non-zero global optimum ($E^* = 15.84$).

| Algorithm | Type | Best Valid Score | Optimality Gap | Runtime |
|---|---|---|---|---|
| **Exhaustive Search** | Exact Classical | **15.84** | 0.00 (optimal) | 73.0 ms |
| **Simulated Annealing** | Metaheuristic Classical | **15.84** | 0.00 (optimal) | 35.5 ms |
| **Greedy Allocation** | Heuristic Classical | 18.00 | +2.16 (13.64%) | 0.15 ms |
| **QAOA (Simulated)** | Variational Quantum | *Skipped* | N/A | Exceeds 18-qubit safety threshold (24 qubits = 268 MB statevector) |

### 2. Unavoidable 5-Node Scenario (`scenarios/unavoidable_5node.json`)
* Nodes: 5, Channels: 3, Qubits: 15, Statevector RAM: 0.5 MB.
* Exact global minimum: **2.40** (6 optimal configurations).

| Algorithm | Type | Best Valid Score | Optimality Gap | Valid Rate | Runtime |
|---|---|---|---|---|---|
| **Exhaustive Search** | Exact Classical | **2.40** | 0.00 (optimal) | 100.0% | 2.6 ms |
| **Greedy Allocation** | Heuristic Classical | **2.40** | 0.00 (optimal) | 100.0% | 0.12 ms |
| **Simulated Annealing** | Metaheuristic Classical | **2.40** | 0.00 (optimal) | 100.0% | 39.1 ms |
| **QAOA $p=1$** | Simulated Quantum | **2.40** | 0.00 (optimal) | 17.92% | 63.2 s opt + 0.02 s |
| **Random Sampling** | Unoptimized Baseline | 4.50 | +2.10 (87.5%) | 0.68% | 0.01 s |

---

## Network Visualizations

RescueMesh automatically generates two distinct visualization views in `results/`:
1. `results/network_graph.png`: Base topology layout with synthetic edge weights.
2. `results/allocated_network.png`: **Channel-colored allocation view** where node circles are colored by assigned channel, resolved links are rendered in muted gray, and active same-channel interference clashes are highlighted with bold crimson lines and explicit clash penalty labels.

---

## Installation & Execution

### Setup
Tested on Linux with Python 3.12.
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Reproducible Execution Commands

#### 1. Reproduce Original Baseline Experiment
Runs the exact 5-node 3-channel benchmark with QAOA $p=1$ and $p=2$, exhaustive search, validation checks, and figure generation:
```bash
python main.py
```

#### 2. Run the Realistic 8-Node Scenario
Evaluates the 8-node scenario with unavoidable interference using classical solvers:
```bash
python main.py --scenario scenarios/realistic_8node.json --no-qaoa
```

#### 3. Run the Unavoidable Interference Scenario with QAOA
Executes QAOA and classical solvers on the 5-node $K_4$ instance:
```bash
python main.py --scenario scenarios/unavoidable_5node.json --p 1 --shots 4096
```

#### 4. Generate a Custom Synthetic Scenario
```bash
python scenario_generator.py --nodes 8 --channels 3 --density 0.45 --seed 42 --out scenarios/custom_8node.json
python main.py --scenario scenarios/custom_8node.json --no-qaoa
```

#### 5. Run Automated Test Suite
Executes 23 automated unit and integration tests:
```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

---

## Project Structure

```
RescueMesh/
├── main.py                 CLI entry point supporting scenarios and baseline reproduction
├── simulation.py           Unified simulation engine (classical & quantum execution)
├── scenario.py             Scenario dataclass, JSON loader, and schema validation
├── scenario_generator.py   Reproducible synthetic scenario generator (clique injection)
├── classical_solver.py     Exhaustive search, Greedy allocation, and Simulated Annealing
├── qubo_model.py           QUBO matrix construction, bit-vector math, and Ising mapping
├── quantum_solver.py       QAOA circuit, Aer state-vector simulation, and memory safety
├── evaluation.py           QUBO mathematical validation and raw-counts verification
├── visualization.py        Topology plotting, channel coloring, and clash highlighting
├── config.py               Original 5-node baseline problem definition (retained)
├── requirements.txt        Pinned dependencies
├── scenarios/              Pre-configured network scenario JSON files
│   ├── original_5node.json
│   ├── unavoidable_5node.json
│   ├── realistic_8node.json
│   └── dense_12node.json
├── tests/                  Comprehensive automated test suite
│   └── test_rescuemesh.py
├── results/                Generated plots, JSON data, and comparison tables
└── report/                 Architecture diagram, report, and demonstration guides
```

---

## References

1. E. Farhi, J. Goldstone, S. Gutmann, *"A Quantum Approximate Optimization Algorithm"*, arXiv:1411.4028 (2014).
2. A. Lucas, *"Ising formulations of many NP problems"*, Frontiers in Physics 2, 5 (2014).
3. A. Javadi-Abhari et al., *"Quantum computing with Qiskit"*, arXiv:2405.08810 (2024).
4. Qiskit Aer Simulator: [https://github.com/Qiskit/qiskit-aer](https://github.com/Qiskit/qiskit-aer).
