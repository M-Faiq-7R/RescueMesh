# RescueMesh
**Quantum-Assisted Channel Allocation for Emergency Wireless Mesh Networks**

A Qiskit Fall Fest 2026 hackathon project exploring QUBO, Ising Hamiltonians, and QAOA for allocating wireless channels in post-disaster emergency mesh networks.

## Overview

After a disaster, cellular infrastructure may become unavailable. Emergency teams can deploy portable wireless mesh nodes for command, medical, rescue, and shelter operations.

When nearby nodes share wireless channels, interference can occur. RescueMesh models this problem as a mathematical optimization task and compares quantum-inspired optimization with classical algorithms.

The project uses:
- QUBO for mathematical formulation.
- Ising Hamiltonians for quantum encoding.
- QAOA for approximate optimization.
- Qiskit Aer for local quantum circuit simulation.
- Exhaustive Search, Greedy Allocation, and Simulated Annealing for classical comparisons.

**Scientific integrity:** This is a simulation using synthetic interference weights, not a real wireless deployment. No quantum advantage or speedup is claimed.

## Mathematical Formulation

Let:
- \(x_{i,c}\in\{0,1\}\): whether node \(i\) uses channel \(c\).
- \(w_{ij}\): interference weight between connected nodes.
- \(P\): penalty for violating channel-assignment constraints.

The QUBO objective is:

\[
\boxed{
E(x)=
\sum_{(i,j)\in E}w_{ij}\sum_{c=1}^{K}x_{i,c}x_{j,c}
+
P\sum_{i=1}^{N}
\left(\sum_{c=1}^{K}x_{i,c}-1\right)^2
}
\]

The first term minimizes interference. The second ensures that every node receives exactly one channel.

The binary variables are converted into Ising variables using:

\[
x_i=\frac{1-Z_i}{2}
\]

This produces a cost Hamiltonian used by QAOA.

## QAOA Implementation

RescueMesh implements the Quantum Approximate Optimization Algorithm using Qiskit Aer.

The circuit alternates between:

1. Initial equal superposition using Hadamard gates.
2. Cost Hamiltonian rotations using RZ and RZZ gates.
3. Mixer Hamiltonian rotations using RX gates.
4. Measurement and classical decoding.
5. Classical parameter optimization using COBYLA.

Experiments use QAOA depths \(p=1\) and \(p=2\).

The quantum circuits are simulated locally using a classical computer. No quantum hardware is required.

## Experimental Results

### Unavoidable-Interference Scenario

The five-node scenario contains a four-node clique (K4) with only three available channels. Therefore, at least one interference conflict is unavoidable.

- Nodes: 5
- Channels: 3
- Edges: 8
- Qubits: 15
- Shots: 4,096
- Exact global optimum: 2.4
- Number of optimal assignments: 6

### QAOA Results

| Metric | QAOA p=1 | QAOA p=2 |
|---|---:|---:|
| Valid solutions | 18.14% | 48.46% |
| Optimal solutions | 0.37% | 1.64% |
| Mean QUBO energy | 51.84 | 40.42 |
| Optimization time | 53.4 s | 17.3 s |
| Best valid interference | 2.4 | 2.4 |

Increasing the QAOA depth from p=1 to p=2 improved the valid-solution and optimal-solution sampling rates in this experiment.

### Classical Comparison

| Algorithm | Best Interference | Runtime |
|---|---:|---:|
| Exhaustive Search | 2.4 | 1.9 ms |
| Greedy Allocation | 2.4 | 0.14 ms |
| Simulated Annealing | 2.4 | 25.99 ms |
| QAOA p=1 | 2.4 | 53.4 s optimization |
| QAOA p=2 | 2.4 | 17.3 s optimization |

These results demonstrate that QAOA can find optimal candidate solutions in this small simulated instance. Classical algorithms remain substantially faster.

Results are from individual experimental runs and should not be interpreted as statistical proof of consistent QAOA improvement.

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/M-Faiq-7R/RescueMesh.git
```

### 2. Enter the project directory

```bash
cd RescueMesh
```

### 3. Create a virtual environment

```bash
python3 -m venv .venv
```

### 4. Activate it

Linux / macOS:

```bash
source .venv/bin/activate
```

Windows:

```powershell
.venv\Scripts\activate
```

### 5. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 6. Verify installation

```bash
python -c "import qiskit, qiskit_aer, networkx; print('Qiskit:', qiskit.__version__); print('Aer:', qiskit_aer.__version__); print('NetworkX:', networkx.__version__)"
```

Tested locally with:
- Python 3.12
- Qiskit 2.6.2
- Qiskit Aer 0.18.2
- NetworkX 3.7

## Running RescueMesh

### Run the default experiment

```bash
python main.py
```

### Run the unavoidable-interference scenario

```bash
python main.py --scenario scenarios/unavoidable_5node.json --p 1 --shots 4096
```

### Run QAOA with p=2

```bash
python main.py --scenario scenarios/unavoidable_5node.json --p 2 --shots 4096
```

### Run the larger eight-node scenario

```bash
python main.py --scenario scenarios/realistic_8node.json --no-qaoa
```

### Run the interactive demonstration

```bash
python demo.py
```

Generated visualizations and experiment outputs are saved under `results/`.

## Running Tests

Execute the automated test suite:

```bash
python -m unittest discover -s tests -v
```

The current local test suite contains 25 tests, covering:
- Classical optimization algorithms.
- QUBO matrix construction.
- QUBO-to-Ising conversion.
- Quantum solver helper functions.
- Scenario validation.
- Visualization.
- Statevector memory calculations.

**Latest local verification:** 25 tests passed.

## Project Structure

```text
RescueMesh/
├── main.py
├── demo.py
├── simulation.py
├── scenario.py
├── scenario_generator.py
├── qubo_model.py
├── quantum_solver.py
├── classical_solver.py
├── evaluation.py
├── visualization.py
├── config.py
├── requirements.txt
├── scenarios/
├── tests/
├── results/
└── report/
```

## Limitations

- Synthetic interference weights rather than measured RF data.
- Small problem instances.
- QAOA executed on a classical statevector simulator.
- Noisy quantum hardware was not tested.
- Classical solvers outperform QAOA in runtime on tested instances.
- Results are individual runs, not a large-scale statistical evaluation.
- No quantum advantage or speedup is demonstrated.

## References

1. Farhi, E., Goldstone, J., and Gutmann, S. *A Quantum Approximate Optimization Algorithm* (2014). https://arxiv.org/abs/1411.4028
2. Lucas, A. *Ising Formulations of Many NP Problems* (2014). https://doi.org/10.3389/fphy.2014.00005
3. Javadi-Abhari et al. *Quantum Computing with Qiskit* (2024). https://arxiv.org/abs/2405.08810
4. Qiskit Aer: https://github.com/Qiskit/qiskit-aer

---

**Developed for Qiskit Fall Fest 2026.**
