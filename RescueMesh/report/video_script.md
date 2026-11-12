# RescueMesh: 3-Minute Demonstration & Presentation Script

**Target Duration**: 3:00 (approx. 420 words at a steady, authoritative research presentation pace).  
**Presenter Role**: Senior Quantum-Computing Researcher & Network Optimization Engineer.

---

## 0:00 - 0:35 | Problem & Operational Context
*(Visual: Slide with post-disaster mesh diagram, then display `results/network_graph.png`)*

"In the immediate aftermath of a natural disaster—such as an earthquake or severe flood—terrestrial cellular infrastructure is frequently incapacitated. First responders deploy portable wireless mesh nodes for incident command, medical triage units, search-and-rescue teams, and emergency shelters.

Because wireless spectrum is severely constrained, adjacent nodes operating on identical channels suffer RF interference and signal degradation. Allocating channels manually under operational duress is error-prone. In RescueMesh, we model this challenge as a Quadratic Unconstrained Binary Optimization (QUBO) problem, mapping priority-weighted channel allocation onto Ising spin systems to evaluate both quantum algorithms and classical optimization heuristics."

---

## 0:35 - 1:15 | Architecture, Priorities & Realistic Scenarios
*(Visual: Display `report/architecture_diagram.png`)*

"Our upgraded framework accepts configurable JSON scenarios with arbitrary topologies, channel capacities, and node operational priorities. For instance, an Incident Command Post carries higher operational priority than an auxiliary supply depot, scaling the penalty of interference clashes.

Unlike trivial 3-colorable networks where interference can be eliminated completely, real deployments experience unavoidable spectrum contention. We demonstrate this on realistic 8-node topologies with embedded high-density cliques where the global optimum is strictly non-zero. The system automatically computes a safe constraint penalty $P$ that strictly exceeds the maximum weighted degree, ensuring invalid channel allocations are never energy-minimizing."

---

## 1:15 - 2:00 | Mathematical Formulation & QAOA on Qiskit Aer
*(Visual: Formula equations, circuit diagram)*

"We formulate the problem using $N \times C$ binary variables $x_{i,c}$, mapped to an Ising Hamiltonian $H_C$ with single-qubit $Z$ fields and two-qubit $ZZ$ couplers.

On Qiskit Aer, the Quantum Approximate Optimization Algorithm (QAOA) prepares an equal superposition state $|+\rangle^{\otimes n}$, alternating cost Hamiltonian rotations $e^{-i\gamma H_C}$ and mixer rotations $e^{-i\beta \sum X_i}$. A classical optimizer tunes $\gamma$ and $\beta$ to minimize the sampled expectation value.

Critically, as quantum researchers, we must respect state-vector memory complexity: storing $n$ qubits requires $2^n \times 16$ bytes. While a 15-qubit instance requires half a megabyte, an 8-node, 3-channel scenario requires 24 qubits—over 268 megabytes per statevector and excessive simulation time. Our framework safely enforces statevector memory guards while retaining exact QAOA execution on small instances."

---

## 2:00 - 2:40 | Live Demonstration & Visualizations
*(Visual: Terminal executing commands, followed by `results/allocated_network.png`)*

"In our live benchmark:
1. First, classical exhaustive search enumerates all $3^8 = 6,561$ configurations of the 8-node scenario in 73 milliseconds, proving the non-zero global minimum of 15.84.
2. Our priority-degree Greedy heuristic delivers a valid solution in 0.15 milliseconds with a 13.6% optimality gap.
3. Simulated Annealing converges to the exact global optimum (15.84) in just 35 milliseconds.
4. On our 15-qubit unavoidable interference scenario, QAOA $p=1$ achieves an 18% valid allocation rate—compared to under 1% for random guessing—and successfully locates the non-zero optimum.

Our new visualization tool automatically colors each node by its assigned channel, renders resolved links in muted gray, and highlights active same-channel clashes in bold crimson with exact clash costs."

---

## 2:40 - 3:00 | Honest Scientific Assessment & Limitations
*(Visual: Summary comparison table)*

"To maintain scientific rigor:
1. **No quantum advantage or speedup is claimed**: classical heuristics solve these problem sizes in milliseconds, whereas simulated QAOA requires dozens of seconds of classical parameter tuning.
2. All weights are synthetic heuristics for simulation, not empirical RF field measurements.
3. Real quantum hardware would face device noise and gate infidelities that do not appear in our ideal simulator.

RescueMesh provides an open, reproducible, and mathematically verified testbed for studying quantum optimization in wireless communications. Thank you."

---

### Anticipated Technical Q&A

* **Q: Why are classical heuristics so much faster than simulated QAOA?**  
  *A:* Simulating a quantum circuit on classical hardware requires matrix-vector multiplications on $2^n$ state vectors, scaling exponentially. On physical QPUs, sampling is fast, but variational parameter optimization on noisy devices remains a fundamental research challenge.

* **Q: How does the priority weighting integrate into the QUBO?**  
  *A:* An edge $(u,v)$ with raw weight $w_{uv}$ and node priorities $p_u, p_v$ is weighted as $w_{uv}^{\text{eff}} = w_{uv} \cdot (p_u \cdot p_v)$. This enters the QUBO as quadratic coefficients $x(u,c)x(v,c)$, maintaining the exact mathematical Ising structure without adding variables.
