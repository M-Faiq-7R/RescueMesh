# RescueMesh

**Quantum-assisted channel allocation for emergency wireless mesh networks** (Qiskit Fall Fest 2026 hackathon project)

RescueMesh assigns wireless channels to five emergency-communication nodes so that nodes that interfere with each other avoid sharing a channel. The problem is written as a QUBO, converted to an Ising Hamiltonian and solved with QAOA on Qiskit's local simulator. An independent exhaustive-search solver provides the exact answer to compare against.

> **Honest summary.** This is a small simulation study on a noiseless simulator. QAOA finds valid and optimal allocations far more often than random sampling, but it uses far more compute than the exact classical solver, which finds all optima in about a millisecond. **No quantum advantage or speedup is claimed.**

![Architecture](report/architecture_diagram.png)

## Real-world use case

After an earthquake or flood, cellular networks may be down. Rescue teams deploy portable mesh nodes (command center, medical unit, rescue teams, shelter). Nearby nodes on the same channel interfere, and spectrum is limited. Choosing channels by hand is error-prone; RescueMesh shows how this can be posed as an optimization problem. It is a simulation, not a real wireless deployment.

## Problem statement

* 5 nodes `A–E`, 3 channels `0, 1, 2`.
* 7 weighted interference edges (synthetic weights): A–B 5, A–C 2, B–C 4, B–D 3, C–D 6, C–E 2, D–E 5.
* Give every node exactly one channel and minimize the total weight of edges whose two ends share a channel.

## Mathematical formulation

Binary variable `x(i,c) = 1` if node `i` uses channel `c` (5 × 3 = 15 variables).

```
Interference  = Σ over edges (i,j)  w_ij · Σ_c  x(i,c) · x(j,c)
Penalty       = P · Σ over nodes i  ( Σ_c x(i,c) − 1 )²
Minimize        E(x) = Interference + Penalty          with P = 15
```

* The interference term is 1 only when both ends of an edge pick the same channel, so it charges the edge weight exactly in that case.
* The penalty is 0 when a node has exactly one channel and ≥ P otherwise (no channel or several channels).
* Using `x² = x`, each node's penalty expands to `P·(1 − Σ_c x(i,c) + 2·Σ_{c<c'} x(i,c)·x(i,c'))`.
* **Why P = 15:** the largest weighted degree is 14 (node C: 2+4+6+2). A penalty above that guarantees that dropping a node's channel can never pay off, whatever the weights. (P = 13 also happens to work on this instance, but P = 15 does not rely on luck.)

## QUBO and Ising

* **QUBO** (Quadratic Unconstrained Binary Optimization): minimize `xᵀQx + offset` over 0/1 variables with no hard constraints. Here Q has 51 non-zero entries and offset 75.
* **Ising:** substituting `x = (1 − z)/2` with `z = ±1` gives `E = const + Σ hᵢ zᵢ + Σ Jᵢⱼ zᵢ zⱼ` with `Jᵢⱼ = Qᵢⱼ/4`, `hᵢ = −Qᵢᵢ/2 − ¼·(sum of Q entries touching i)`. That is 15 `Z` terms and 36 `ZZ` terms (constant 95.25).
* All 2¹⁵ = 32,768 bit patterns are checked: valid patterns have energy equal to the true interference, invalid ones are penalized, the lowest invalid energy (15) is above the valid optimum (0), and Ising energy equals QUBO energy everywhere.

## QAOA implementation (`quantum_solver.py`)

1. Hadamard on all 15 qubits (equal superposition of all bit patterns).
2. **Cost layer** `exp(−iγH)`: `RZ(2γh)` per qubit and `RZZ(2γJ)` per coupling. It tags each pattern with a phase set by its energy.
3. **Mixer layer** `exp(−iβΣX)`: `RX(2β)` on each qubit, so phases interfere and low-energy patterns gain probability.
4. Measure all qubits (8,192 shots). A classical optimizer (grid search + COBYLA, scipy) tunes `γ, β` to minimize the **sampled mean energy**.
5. Decode bitstrings (Qiskit prints qubit 0 as the **rightmost** character) into node-channel assignments; valid = every node has exactly one channel.

Executed with `qiskit` + `qiskit-aer` (`AerSimulator`, state-vector method, fixed seed 42). Experiments use p = 1 and, optionally, p = 2.

*Implementation note:* an earlier version bound circuit parameters from a plain list, which Qiskit orders alphabetically (`beta` before `gamma`), silently swapping γ and β. Parameters are now bound by name and a test checks it. All reported results come from the corrected code.

## Classical baseline (`classical_solver.py`)

Independent of Qiskit: enumerates all 3⁵ = 243 assignments, scores each, and returns the exact optimum (interference **0**) with all **6** optimal assignments (channel relabellings of one pattern). Six validation checks run on it.

## Results

Same budget for all sampled methods: **8,192 samples**, seed 42 (full output in `results/phase5_results.json`).

| Method | Valid samples | Optimal samples | Distinct optima found | Best valid score | Mean energy (all samples) |
|---|---|---|---|---|---|
| Random sampling | 62 (0.76%) | 2 (0.02%) | 2 of 6 | 0 | 95.61 |
| QAOA p = 1 | 1,461 (17.83%) | 43 (0.52%) | 6 of 6 | 0 | 31.93 |
| QAOA p = 2 | 2,288 (27.93%) | 82 (1.00%) | 6 of 6 | 0 | 28.50 |
| Exhaustive search (243 enumerated, all valid) | 243 (100%) | 6 (2.47% of assignments) | 6 of 6 | 0 | n/a* |

\*The exhaustive mean interference over the 243 valid assignments is 9.00. It is **not comparable** to the sampled mean energies, which include the penalty of invalid samples.

* Exact global optimum: 0; gap of every method's best valid result: 0. **The random baseline also found optimal allocations (2 samples).** Reaching the optimum therefore proves little; the difference is how often. Uniform sampling would be expected to give about 61 valid and 1.5 optimal samples out of 8,192.
* 82.17% (p = 1) and 72.07% (p = 2) of QAOA samples are still invalid.
* p = 2 used a different optimization effort (8 COBYLA starts, 758 circuit evaluations vs 2,642 for the p = 1 grid + COBYLA). It is a single run, so its improvement is **suggestive, not conclusive**.
* Runtime in the clean-environment run (CPU simulation, varies by machine): exhaustive 1.6 ms; random sampling 0.07 s; QAOA p = 1 91 s optimization + 0.09 s sampling; p = 2 34 s optimization + 0.08 s sampling.

Figures are written to `results/` (`network_graph.png`, `fig1`–`fig5`).

## Installation

Tested with Python 3.12.3 on Linux. From the project folder:

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Pinned dependencies: `qiskit==2.6.2`, `qiskit-aer==0.18.2`, `numpy==2.5.4`, `scipy==1.18.1`, `networkx==3.7`, `matplotlib==3.11.2`.

## Execution

```bash
python main.py
```

This runs every phase (about 2 minutes; QAOA parameter optimization dominates), prints all checks and tables, and writes `results/*.png`, `results/*.json`, `results/comparison_table.csv` and `report/architecture_diagram.png`. Results are reproducible (fixed seeds); only the runtimes vary.

Example output (excerpt from a real run):

```
Minimum interference (global optimum): 0
Number of optimal assignments (channel relabellings): 6
...
  Method            | Samples        | Valid (count, %) | Optimal (count, %) | Distinct optima | ...
  Random sampling   | 8192           | 62 (0.76%)       | 2 (0.02%)          | 2 of 6          | ...
  QAOA p=1          | 8192           | 1461 (17.83%)    | 43 (0.52%)         | 6 of 6          | ...
  QAOA p=2          | 8192           | 2288 (27.93%)    | 82 (1.00%)         | 6 of 6          | ...
Independent verification from raw counts:
  [PASS] QAOA p=1: counts, percentages and mean energy recomputed from raw bitstrings
```

Optional: `report/build_report.js` regenerates the Word report from `results/phase5_results.json` (needs Node.js and the `docx` npm package; not required to reproduce the experiments).

## Project structure

```
RescueMesh/
├── main.py               runs all phases, prints checks/tables, saves results and figures
├── config.py             the fixed instance: nodes, channels, edges, penalty P = 15
├── graph_generator.py    builds the weighted interference graph (NetworkX)
├── qubo_model.py         QUBO matrix, bit-pattern helpers, QUBO -> Ising conversion
├── quantum_solver.py     QAOA circuit, Aer simulation, optimizer, decoding (Qiskit)
├── classical_solver.py   exhaustive search + validation (no Qiskit)
├── evaluation.py         QUBO validation, sample statistics, verification from raw counts
├── visualization.py      network plot, comparison figures, architecture diagram
├── requirements.txt      pinned dependencies
├── results/              figures, phase5_results.json, qaoa_results.json, comparison_table.csv
└── report/               architecture diagram, report, video script, build_report.js
```

## Limitations

* Tiny instance (5 nodes, 15 qubits) with a **zero-interference optimum** (the graph is 3-colourable), which makes it relatively easy.
* **Noiseless simulator only**; no quantum hardware or noise model was tested.
* No quantum speedup or advantage is demonstrated; exhaustive search is exact and much cheaper here.
* High share of invalid measurements (72–82%), and QAOA quality depends on **classical parameter optimization**; the γ search covers only [0, π/2] and its grid was informed by an exact diagnostic scan.
* p = 2 is one run with different optimizer effort; no statistical study over seeds was done.
* Interference weights are synthetic, not measured radio data.

## References

1. E. Farhi, J. Goldstone, S. Gutmann, "A Quantum Approximate Optimization Algorithm", arXiv:1411.4028 (2014).
2. A. Lucas, "Ising formulations of many NP problems", Frontiers in Physics 2, 5 (2014), doi:10.3389/fphy.2014.00005.
3. A. Javadi-Abhari et al., "Quantum computing with Qiskit", arXiv:2405.08810 (2024).
4. Qiskit Aer simulator: https://github.com/Qiskit/qiskit-aer
5. Software: SciPy (https://scipy.org), NetworkX (https://networkx.org), Matplotlib (https://matplotlib.org).
