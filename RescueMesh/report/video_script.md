# RescueMesh — 3-Minute Demonstration Script

**Purpose:** Present the problem, model, working implementation, measured results, and limitations without overstating the quantum component.

## 0:00–0:35 | Problem

“After a disaster, cellular infrastructure may be unavailable. Response teams can deploy portable mesh nodes for incident command, medical triage, rescue, shelters, and logistics. Nearby nodes sharing a channel can interfere with one another. RescueMesh models channel allocation as an optimization problem and compares classical solvers with QAOA.”

*Show:* `results/network_graph.png`

## 0:35–1:10 | System and mathematical model

“Each node must be assigned exactly one available channel. We represent the network as a weighted graph. The objective penalizes connected nodes that use the same channel, while a one-hot penalty enforces exactly one channel per node. Node priorities scale the effective edge weights. We encode this objective as a QUBO, then convert it to an Ising Hamiltonian.”

*Show:* `report/architecture_diagram.png` and the QUBO objective in the technical README.

## 1:10–1:50 | Classical and quantum methods

“The framework includes exhaustive search for manageable instances, greedy allocation, and simulated annealing. For the quantum experiment, QAOA prepares a superposition, alternates cost and mixer layers, and uses a classical optimizer to tune circuit parameters. We execute the circuit with Qiskit Aer on a classical computer, not on quantum hardware.”

“Statevector simulation scales exponentially with qubit count. Our default safety threshold is 18 qubits, so the 8-node, 3-channel scenario is run with classical methods rather than forcing a 24-qubit simulation.”

## 1:50–2:35 | Demonstration and results

*Run the 8-node classical case:*

```bash
python main.py --scenario scenarios/realistic_8node.json --no-qaoa
```

“The exact solver evaluates 6,561 assignments and finds an interference score of 15.84. The simulated annealing baseline also reaches this optimum in the recorded run. The allocation visualization highlights same-channel conflicts.”

*Run the 5-node QAOA case:*

```bash
python main.py --scenario scenarios/unavoidable_5node.json --p 2 --shots 4096
```

“This five-node graph contains a four-node clique but only three channels, so at least one conflict is unavoidable. The exact optimum is 2.40, with six optimal assignments. In the recorded 4,096-shot experiment, QAOA p=1 sampled 18.14% valid allocations and 0.37% optimal allocations. QAOA p=2 sampled 48.46% valid and 1.64% optimal allocations. Both depths found the exact optimum among their valid samples.”

## 2:35–3:00 | Honest assessment

“These are individual simulation runs, not statistical proof of general QAOA improvement. Classical methods solve the same small instance in milliseconds, while QAOA parameter optimization takes seconds. All link weights are synthetic; we have not measured real RF or SINR data. The contribution is a reproducible, mathematically checked optimization pipeline—not a claim of quantum advantage.”

“RescueMesh demonstrates how a constrained emergency channel-allocation problem can be formulated, validated, visualized, and used to compare classical and simulated quantum optimization.”

---

## Anticipated judge questions

**Why is the four-node clique important?**  
A clique of four nodes requires four distinct channels to avoid all same-channel conflicts. With only three channels, at least one conflict is unavoidable.

**What is QAOA actually running on?**  
Qiskit Aer statevector simulation on a classical computer. No physical QPU is used.

**Why does QAOA take longer than the classical solvers?**  
The simulator evolves a statevector whose size grows exponentially with qubit count, and the variational parameters require repeated circuit evaluations. For these small instances, classical algorithms are substantially faster.

**What does the valid-sample rate mean?**  
The fraction of measured bitstrings that assign exactly one channel to every node. The optimal-sample rate is the fraction that also achieves the exact minimum interference score.

**Does p=2 always run faster or perform better than p=1?**  
No. The reported improvement is specific to this recorded run and optimizer path. Repeated runs across seeds and instances would be needed for a broader conclusion.

**Are the edge weights real RF measurements?**  
No. They are synthetic scenario weights used to test the optimization formulation. The project does not model propagation, RSSI, or SINR.
