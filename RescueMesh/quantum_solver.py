"""quantum_solver.py - QAOA (p layers) on the RescueMesh Ising Hamiltonian.

Needs: qiskit (circuits, SparsePauliOp, Statevector) and qiskit-aer (simulator).
Nothing from classical_solver.py is used here: the quantum side only sees the
QUBO matrix Q (+ offset) and the Ising coefficients (h, J, const).

QAOA in one paragraph
---------------------
1. START: put all n qubits in the equal superposition |+>^n (a Hadamard on
   each). Every one of the 2^n bit patterns has the same amplitude.
2. COST LAYER: exp(-i * gamma * H_C). H_C is the Ising Hamiltonian
   (const + sum h_i Z_i + sum J_ij Z_i Z_j). Its "energy" of a bit pattern is
   exactly our QUBO energy. This layer does not change how likely a pattern is;
   it adds a phase that depends on the pattern's energy.
3. MIXER LAYER: exp(-i * beta * sum_i X_i), i.e. an RX rotation on every qubit.
   It mixes neighbouring bit patterns so the phases from step 2 interfere:
   patterns whose phases line up constructively gain probability. Without the
   mixer the cost layer would change nothing we can measure.
4. Repeat 2-3 p times, then MEASURE every qubit. Each run (a "shot") returns one
   bit pattern at random, with probability |amplitude|^2.
5. A classical optimizer changes (gamma, beta) to push the AVERAGE measured
   energy down. Good parameters make low-energy patterns more likely.

State-vector simulator memory complexity
----------------------------------------
A classical state-vector simulation tracks all 2^n complex amplitudes (16 bytes each).
Memory scales strictly as O(2^n). For n=15 qubits, memory is ~0.5 MB. For n=24 qubits
(e.g., 8 nodes x 3 channels), memory reaches ~268 MB per statevector and parameter
optimization involves hundreds of evaluations. Instances with n > 18 qubits are
safely warned or skipped by default.
NO QUANTUM ADVANTAGE OR SPEEDUP IS CLAIMED.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.circuit import ParameterVector
from qiskit.quantum_info import SparsePauliOp, Statevector
from qiskit_aer import AerSimulator

import config
from qubo_model import decode


# ------------------------------------------------ Memory & Feasibility Helpers
def calculate_statevector_memory_mb(n_qubits: int) -> float:
    """Calculate RAM in Megabytes required to store a statevector of n_qubits.

    Each complex128 amplitude requires 16 bytes.
    RAM (MB) = (2^n * 16) / (1024^2) = 2^(n - 16) MB.
    """
    return float((2 ** n_qubits * 16) / (1024 * 1024))


def check_qaoa_feasibility(
    n_nodes: int, n_channels: int, max_qubits: int = 18
) -> Tuple[bool, str, float]:
    """Check whether QAOA state-vector simulation is computationally feasible.

    Returns:
        (is_feasible, diagnostic_message, memory_estimate_mb)
    """
    n_qubits = n_nodes * n_channels
    mem_mb = calculate_statevector_memory_mb(n_qubits)

    if n_qubits > max_qubits:
        msg = (
            f"QAOA requires {n_qubits} qubits ({n_nodes} nodes x {n_channels} channels), "
            f"which needs {mem_mb:.1f} MB for each statevector and exponential classical CPU time. "
            f"State-vector simulation exceeds recommended limit of {max_qubits} qubits. "
            "Skipping QAOA execution to prevent memory exhaustion / long delays."
        )
        return False, msg, mem_mb
    else:
        msg = (
            f"QAOA feasible: {n_qubits} qubits ({n_nodes}x{n_channels}), "
            f"estimated statevector RAM: {mem_mb:.2f} MB."
        )
        return True, msg, mem_mb


# ---------------------------------------------------------------- Hamiltonian
def build_cost_hamiltonian(h, J, const):
    """Ising Hamiltonian as a SparsePauliOp: const*I + sum h_i Z_i + sum J_ij Z_i Z_j.

    ("Z", [i], h_i) means: a Pauli Z acting on qubit i with coefficient h_i.
    """
    n = len(h)
    terms = [("I", [0], float(const))]
    terms += [("Z", [i], float(h[i])) for i in range(n) if h[i] != 0]
    terms += [("ZZ", [i, j], float(v)) for (i, j), v in J.items()]
    return SparsePauliOp.from_sparse_list(terms, num_qubits=n)


# -------------------------------------------------------------------- circuit
def build_qaoa_circuit(h, J, p=1, measure=True):
    """Parameterized QAOA circuit. Parameters: gamma_0..gamma_{p-1}, beta_0..beta_{p-1}.

    A ParameterVector is a list of unbound numbers; we plug in values later with
    assign_parameters, so the circuit is built (and transpiled) only once.
    """
    n = len(h)
    gamma = ParameterVector("gamma", p)
    beta = ParameterVector("beta", p)
    qc = QuantumCircuit(n)
    qc.h(range(n))                                   # initial state |+>^n
    for layer in range(p):
        for i in range(n):                           # cost layer, single-Z terms
            if h[i] != 0:
                qc.rz(2 * gamma[layer] * float(h[i]), i)
        for (i, j), value in J.items():              # cost layer, ZZ terms
            qc.rzz(2 * gamma[layer] * float(value), i, j)
        for i in range(n):                           # mixer layer
            qc.rx(2 * beta[layer], i)
    if measure:
        qc.measure_all()                             # adds classical bits "meas"
    return qc


# ------------------------------------------------------------- energy helpers
class EnergyTable:
    """Computes the QUBO energy x^T Q x + offset of a measured bitstring.

    Qiskit gives the string with qubit 0 on the RIGHT, so we reverse it:
    x[k] = string[-1 - k]. Results are cached because many shots repeat.
    """

    def __init__(self, Q, offset):
        self.Q, self.offset, self._cache = Q, offset, {}

    def bits(self, bitstring):
        return np.array([int(bitstring[-1 - k]) for k in range(len(bitstring))])

    def energy(self, bitstring):
        if bitstring not in self._cache:
            x = self.bits(bitstring)
            self._cache[bitstring] = float(x @ self.Q @ x + self.offset)
        return self._cache[bitstring]


def mean_energy(counts, table):
    """Average QUBO energy over all shots (this is what the optimizer minimizes)."""
    shots = sum(counts.values())
    return sum(c * table.energy(b) for b, c in counts.items()) / shots


# ------------------------------------------------------------------ the solver
class QAOASolver:
    def __init__(self, Q, offset, h, J, const, p=1, shots=4096, seed=42):
        self.p, self.shots, self.seed = p, shots, seed
        self.table = EnergyTable(Q, offset)
        self.hamiltonian = build_cost_hamiltonian(h, J, const)
        self.backend = AerSimulator(method="statevector")   # exact local state-vector simulator
        self.circuit = build_qaoa_circuit(h, J, p, measure=True)
        self.circuit_nomeas = build_qaoa_circuit(h, J, p, measure=False)
        # Transpile once: rewrites gates into ones the simulator accepts.
        self.compiled = transpile(self.circuit, self.backend, seed_transpiler=seed)
        self.n_evaluations = 0
        self.history = []                                   # (params, mean energy) per evaluation

    def _bind(self, circuit, params):
        """params = [gamma_0..gamma_{p-1}, beta_0..beta_{p-1}].

        Binding is done BY NAME. (Passing a plain list would bind in the circuit's
        alphabetical order, beta before gamma, and silently swap the two.)
        """
        mapping = {}
        for parameter in circuit.parameters:
            kind, index = parameter.name[:-1].split("[")      # "gamma[0]" -> ("gamma", "0")
            mapping[parameter] = float(params[int(index)] if kind == "gamma"
                                       else params[self.p + int(index)])
        return circuit.assign_parameters(mapping)

    def sample(self, params, shots=None):
        """Run the circuit `shots` times; return {bitstring: count}."""
        bound = self._bind(self.compiled, params)
        job = self.backend.run(bound, shots=shots or self.shots, seed_simulator=self.seed)
        return job.result().get_counts()

    def objective(self, params):
        """Average measured energy for these (gamma, beta). Lower = better."""
        self.n_evaluations += 1
        value = mean_energy(self.sample(params), self.table)
        self.history.append((list(map(float, params)), value))
        return value

    def exact_probabilities(self, params):
        """Exact probability of each of the 2^n patterns (index r = bit pattern, qubit k = bit k of r).
        Used only for diagnostics; the optimizer never sees it."""
        state = Statevector(self._bind(self.circuit_nomeas, params))
        return state.probabilities()

    def optimize(self, beta_points=61, maxiter=80):
        """1) coarse grid over (gamma, beta) to find a good start  2) COBYLA refinement.
        COBYLA is a classical optimizer that needs no gradients (from scipy)."""
        from scipy.optimize import minimize
        gammas = np.unique(np.concatenate([np.linspace(0, 0.3, 31), np.linspace(0.3, np.pi / 2, 13)]))
        betas = np.linspace(0, np.pi, beta_points)
        best = None
        if self.p == 1:
            for b in betas:
                for g in gammas:
                    v = self.objective([g, b])
                    if best is None or v < best[1]:
                        best = ([g, b], v)
            start = best[0]
        else:
            start = [0.1] * self.p + [0.4] * self.p
        res = minimize(self.objective, start, method="COBYLA",
                       options={"maxiter": maxiter, "rhobeg": 0.02})
        return np.array(res.x), float(res.fun)

    def optimize_from_starts(self, starts, maxiter=300, rhobegs=(0.1, 0.03)):
        """Local COBYLA refinement from several starting points."""
        from scipy.optimize import minimize
        best = None
        for start in starts:
            x = np.array(start, dtype=float)
            for rb in rhobegs:
                res = minimize(self.objective, x, method="COBYLA",
                               options={"maxiter": maxiter, "rhobeg": rb, "tol": 1e-6})
                x = res.x
            if best is None or res.fun < best[1]:
                best = (np.array(res.x), float(res.fun))
        return best


# ------------------------------------------------------------------- decoding
def analyze_counts(counts, table, nodes=None, channels=None):
    """Turn raw counts into a list of candidate records, sorted by count."""
    nodes = config.NODES if nodes is None else list(nodes)
    channels = config.CHANNELS if channels is None else list(channels)
    rows = []
    for bitstring, count in counts.items():
        x = table.bits(bitstring)
        assignment = decode(x, nodes, channels)             # None if invalid
        rows.append({"bitstring": bitstring, "count": count,
                     "energy": table.energy(bitstring),
                     "valid": assignment is not None, "assignment": assignment})
    rows.sort(key=lambda r: -r["count"])
    return rows
