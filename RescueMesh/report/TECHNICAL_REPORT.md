# RescueMesh — Technical Report

**Project:** Quantum-assisted channel allocation for emergency wireless mesh networks  
**Framework:** Python, Qiskit, Qiskit Aer  
**Evaluation mode:** Classical algorithms and noiseless statevector simulation  
**Status:** Reproducible research prototype; not a deployed radio system

## Abstract

RescueMesh models channel assignment in an emergency wireless mesh as a weighted graph optimization problem. Each node must receive exactly one channel, while adjacent nodes using the same channel incur a weighted interference cost. The project constructs a quadratic unconstrained binary optimization (QUBO) model, converts it to an Ising Hamiltonian, and evaluates the Quantum Approximate Optimization Algorithm (QAOA) using Qiskit Aer. Classical exhaustive search, greedy allocation, and simulated annealing provide comparison baselines.

The principal QAOA experiment uses a deliberately constrained five-node graph with a four-node clique and three available channels. This forces a non-zero minimum interference score. Exact enumeration establishes the optimum before QAOA results are evaluated. The experiment demonstrates a working formulation and validation pipeline; it does **not** establish quantum advantage.

## 1. Problem and scope

During disaster response, cellular infrastructure may be unavailable. Portable mesh nodes can support communication among command, medical, rescue, and shelter teams. Assigning channels to nearby nodes is a constrained optimization problem because nodes sharing a channel may interfere.

RescueMesh is a **simulation and optimization prototype**. It does not configure physical radios, measure RF propagation, calculate empirical SINR, or provide a field-ready communications network. Edge weights are synthetic scenario inputs.

## 2. Mathematical formulation

Represent the network as a weighted undirected graph (G=(V,E)). Each edge ((i,j)) has non-negative weight (w_{ij}), representing the modeled cost when connected nodes use the same channel.

Let (C) be the set of available channels and define binary variables:

[
x_{ic}=\begin{cases}1 & \text{if node }i\text{ receives channel }c\\0 & \text{otherwise.}\end{cases}
]

The modeled interference objective is:

[
I(x)=\sum_{(i,j)\in E}w_{ij}\sum_{c\in C}x_{ic}x_{jc}.
]

Exactly-one-channel constraints require:

[
\sum_{c\in C}x_{ic}=1\quad\forall i\in V.
]

The QUBO objective adds a one-hot penalty:

[
E(x)=I(x)+P\sum_{i\in V}\left(\sum_{c\in C}x_{ic}-1\right)^2.
]

Here (P) is selected large enough that violating the one-hot constraint is not beneficial. For priority-aware scenarios, effective edge weights are scaled using the endpoint priorities as defined by the implementation.

## 3. QUBO and Ising representation

The binary objective is expanded into a quadratic form and mapped to an Ising Hamiltonian using (x_k=(1-z_k)/2), where (z_k\in\{-1,+1\}). The resulting Hamiltonian contains single-qubit (Z) terms and pairwise (ZZ) couplings, plus a constant offset.

The implementation validates the conversion numerically: QUBO and Ising energies should agree for every tested bitstring, up to floating-point tolerance. Feasible bitstrings are also checked against the independent classical interference calculation. These checks are essential because a low QUBO energy alone is not sufficient evidence that the decoded allocation is valid.

## 4. QAOA implementation

QAOA alternates a cost unitary derived from the Ising Hamiltonian with an (X)-mixer unitary. Hadamard gates initialize a uniform superposition. A classical optimizer tunes the variational angles, and measurements are decoded into node-to-channel assignments.

The circuit is executed using **Qiskit Aer on a classical computer**. It is not executed on a quantum processing unit. Statevector simulation has exponential memory growth with qubit count, so the application enforces a qubit safety threshold unless explicitly overridden.

A parameter-binding issue was identified during development: relying on an unlabelled parameter list could bind the cost and mixer parameters in the wrong order. The corrected implementation binds parameters by name and verifies that cost angles control the (RZ/RZZ) gates and mixer angles control the (RX) gates.

## 5. Main constrained benchmark

The current recorded benchmark is `scenarios/unavoidable_5node.json`:

| Property | Value |
|---|---:|
| Nodes | 5 |
| Channels | 3 |
| Edges | 8 |
| Binary variables / qubits | 15 |
| Total assignments | (3^5=243) |
| Exact optimum | 2.40 |
| Number of optimal assignments | 6 |
| QUBO penalty | 25.0 |

The graph contains a four-node clique. A clique of four nodes cannot be assigned four distinct channels when only three channels are available; therefore at least one same-channel conflict is unavoidable. Exact enumeration establishes the minimum score of 2.40.

### Recorded QAOA results (4,096 final measurement shots)

| Metric | Random bitstring baseline | QAOA p=1 | QAOA p=2 |
|---|---:|---:|---:|
| Valid samples | 30 (0.73%) | 743 (18.14%) | 1,985 (48.46%) |
| Optimal samples | 1 (0.02%) | 15 (0.37%) | 67 (1.64%) |
| Mean energy across all samples | 153.20 | 51.84 | 40.42 |
| Best valid interference score | 2.40 | 2.40 | 2.40 |

The p=1 optimizer used 2,643 evaluations (about 52–53 seconds in the recorded run). The p=2 run used 746 evaluations (about 17 seconds). These are measured optimizer runs, not a controlled comparison of circuit-depth cost: the optimization strategies and evaluation counts differed. It would be incorrect to infer that p=2 inherently runs faster.

The QAOA mean energy includes penalty contributions from invalid bitstrings; the best valid interference score is computed only after feasibility filtering. The two quantities should not be conflated.

### Interpretation

- Both QAOA depths sampled allocations attaining the exact classical optimum.
- The recorded p=2 run produced a higher valid-sample and optimal-sample fraction than p=1.
- These are individual recorded runs, not multi-seed statistical evidence.
- Classical exhaustive search evaluates only 243 assignments and finds the optimum in milliseconds. Greedy and simulated annealing also reached 2.40 in the recorded benchmark.
- A noiseless statevector simulation does not demonstrate quantum speedup or quantum advantage.

## 6. Additional scenario scaling

The repository includes additional scenarios to demonstrate the scaling limits of exhaustive search and statevector simulation.

| Scenario | Nodes | Channels | Edges | Valid assignments | Evaluation approach |
|---|---:|---:|---:|---:|---|
| Original baseline | 5 | 3 | 7 | 243 | Exact + classical + QAOA-capable |
| Unavoidable benchmark | 5 | 3 | 8 | 243 | Exact + classical + QAOA |
| Realistic scenario | 8 | 3 | 15 | 6,561 | Classical; QAOA skipped by 18-qubit safety guard |
| Dense scenario | 12 | 4 | scenario-defined | 16,777,216 | Classical heuristics; exhaustive enumeration is expensive |

The 8-node case has 24 binary variables/qubits, exceeding the default 18-qubit statevector safety threshold. The 12-node case has 48 binary variables/qubits, making statevector simulation impractical on ordinary hardware. The safety guard is intentional and should not be bypassed casually.

## 7. Validation and testing

The project includes unit tests for the classical solvers, QUBO construction, Ising conversion, scenario validation, visualization helpers, and quantum utility functions. The previously recorded local test run reported **25 tests passing**. That result refers to the tested local checkout at the time; it is not a claim that CI has run on every commit in this branch.

The benchmark pipeline additionally checks:
- QUBO energy against classical interference plus constraint penalties.
- Zero penalty for feasible assignments and a positive penalty for invalid assignments.
- Agreement between QUBO and Ising energies.
- Agreement between QUBO minimizers and exact classical optima.
- Correct Qiskit bit-order decoding and named parameter binding.

## 8. Reproduction

From the application directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m unittest discover -s tests -v
```

Run the constrained QAOA benchmark:

```bash
python main.py --scenario scenarios/unavoidable_5node.json --p 1 --shots 4096
python main.py --scenario scenarios/unavoidable_5node.json --p 2 --shots 4096
```

Run the larger classical scenario:

```bash
python main.py --scenario scenarios/realistic_8node.json --no-qaoa
```

Exact runtimes and stochastic optimizer outputs can vary by machine, dependency versions, and execution conditions. Use the saved experiment artifacts when comparing with the recorded figures.

## 9. Limitations

1. Edge weights are synthetic and are not measured RF/SINR data.
2. The network and channel model omit propagation, fading, mobility, traffic demand, and real radio constraints.
3. QAOA results use a noiseless classical statevector simulator, not quantum hardware.
4. The benchmark is small; classical exact search is decisively cheaper for this instance.
5. The reported p=1/p=2 comparison is based on individual runs with different optimization effort.
6. No quantum speedup, quantum advantage, or deployment readiness is claimed.

## 10. Future work

- Evaluate multiple graph families, sizes, and random seeds.
- Introduce realistic RF measurements and a richer interference model.
- Compare against stronger classical optimization baselines on larger instances.
- Study constraint-preserving mixers and penalty selection.
- Evaluate noise models and, if accessible, real quantum hardware.

## 11. Conclusion

RescueMesh demonstrates an end-to-end workflow for modeling emergency mesh channel allocation, constructing and validating a QUBO and Ising Hamiltonian, executing QAOA in simulation, and comparing measured samples with classical baselines. The constrained five-node benchmark confirms that the implementation can sample optimal allocations, while the classical results establish that this small instance does not benefit computationally from QAOA. The contribution is a reproducible optimization and validation prototype with explicit limitations—not a claim of quantum advantage.
