# RescueMesh Demonstration Guide

This guide provides reproducible step-by-step commands to demonstrate each capability of the upgraded RescueMesh framework.

---

## Prerequisites
Ensure the virtual environment is active:
```bash
source .venv/bin/activate
```

---

## 1. Automated Verification & Test Suite
Run the 23 automated tests covering schema validation, edge checks, synthetic generation, classical solvers, QUBO math, and quantum memory bounds:
```bash
python -m unittest discover -s tests -p "test_*.py" -v
```
*Expected*: All 23 tests pass with `OK` in under 1 second.

---

## 2. Realistic 8-Node Disaster Response Scenario (Unavoidable Interference)
Execute the 8-node tactical mesh scenario where spectrum is limited to 3 channels and high-density core clashes make interference mathematically unavoidable ($E^* > 0$):
```bash
python main.py --scenario scenarios/realistic_8node.json --no-qaoa
```
*Key outputs to highlight*:
* Exhaustive search evaluates all $3^8 = 6,561$ configurations in ~73 ms.
* Proves the non-zero global minimum: **15.84**.
* Priority-degree Greedy allocates channels in ~0.15 ms with an optimality gap of 13.6%.
* Simulated Annealing reaches the exact global optimum (15.84) in ~35 ms.
* Network visualization saved to `results/allocated_network.png` showing node channel colors and active clashes highlighted in bold crimson.

---

## 3. Quantum QAOA on Unavoidable Interference Scenario (15 Qubits)
Run QAOA ($p=1$) on a 5-node scenario containing a 4-clique with 3 channels (unavoidable optimum = 2.40):
```bash
python main.py --scenario scenarios/unavoidable_5node.json --p 1 --shots 2048
```
*Key outputs to highlight*:
* Feasibility check verifies 15 qubits requires only 0.5 MB statevector RAM.
* QAOA increases valid allocation frequency from 0.68% (random) to ~18%.
* QAOA successfully samples the non-zero optimal allocation (2.40).
* Independent verification confirms energy and counts from raw bitstrings.

---

## 4. Reproduce the Original Baseline Benchmark (Original 5-Node Instance)
Run the complete original benchmark with QAOA $p=1$ and $p=2$ on the 3-colorable 5-node graph:
```bash
python main.py
```
*Key outputs to highlight*:
* Full backwards compatibility: produces `results/phase5_results.json`, `fig1`–`fig5`, `results/qaoa_results.json`, and `report/architecture_diagram.png`.
* All QUBO and exhaustive search validation checks pass.

---

## 5. Generate and Test an Arbitrary Synthetic Scenario
Generate a 10-node 3-channel mesh topology with guaranteed unavoidable interference, and evaluate it:
```bash
python scenario_generator.py --nodes 10 --channels 3 --density 0.40 --seed 99 --out scenarios/test_10node.json
python main.py --scenario scenarios/test_10node.json --no-qaoa
```

---

## 6. Inspect Results and Visualizations
Check the generated artifacts in `results/`:
* `results/network_graph.png`: Topology with edge weights.
* `results/allocated_network.png`: Topology with nodes colored by channel and clash links highlighted in bold red.
* `results/experiment_results.json`: Complete structured JSON output.
* `results/comparison_table.csv`: CSV comparison table.
