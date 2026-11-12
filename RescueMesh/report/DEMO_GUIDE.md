# RescueMesh — Demonstration Guide

This guide provides a short, reproducible sequence for presenting the project. Run commands from the application directory:

```bash
cd RescueMesh
source .venv/bin/activate
```

## 1. Verify the codebase

```bash
python -m unittest discover -s tests -v
```

The latest recorded local verification was 25 passing tests. Re-run this command on the presentation machine rather than relying solely on the recorded result.

## 2. Show the 8-node emergency mesh

```bash
python main.py --scenario scenarios/realistic_8node.json --no-qaoa
```

Talking points:
- 8 nodes, 3 channels, and 15 synthetic interference links.
- The recorded exact search evaluated (3^8 = 6,561) valid assignments and found a minimum interference score of 15.84.
- QAOA is intentionally skipped: this scenario requires 24 qubits, above the default 18-qubit statevector guard.
- The output includes a channel allocation plot with same-channel clashes highlighted.

## 3. Show QAOA on the 5-node unavoidable-interference case

```bash
python main.py --scenario scenarios/unavoidable_5node.json --p 2 --shots 4096
```

Talking points:
- The graph contains a four-node clique but only three channels, so at least one conflict is unavoidable.
- The exact classical optimum is 2.40, with six optimal assignments.
- QAOA p=1 and p=2 are sampled and compared with random bitstring sampling.
- The recorded run observed 18.14% / 48.46% valid samples and 0.37% / 1.64% optimal samples for p=1 / p=2, respectively.
- Classical solvers reach the exact optimum in milliseconds on this small problem; do not present QAOA as faster.

## 4. Generate a new synthetic scenario

```bash
python main.py --generate-scenario --nodes 8 --channels 3 --density 0.45 --seed 42 --no-qaoa
```

This generates a synthetic topology and evaluates it with the classical methods. Change the seed to generate a different reproducible instance.

## 5. Inspect artifacts

Look in `results/` (or the selected `--outdir`) for:
- `network_graph.png`
- `allocated_network.png`
- `experiment_results.json`
- `comparison_table.csv`

## Judge-facing caveats

- Edge weights are synthetic heuristics, not measured RF/SINR values.
- QAOA uses Qiskit Aer on a classical computer; no QPU was used.
- A better sample percentage in one run is not proof of a general advantage.
- Statevector memory grows exponentially with qubit count.
