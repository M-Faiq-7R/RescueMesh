"""qubo_model.py - builds the QUBO and converts it to an Ising Hamiltonian.

Pure NumPy, no Qiskit here, so every step can be checked by hand.

QUBO = Quadratic Unconstrained Binary Optimization:
    minimize   E(x) = sum_i Q[i,i]*x_i + sum_{i<j} Q[i,j]*x_i*x_j + offset
    where every x_i is 0 or 1 and there are NO hard constraints.
(Because x_i is 0 or 1, x_i*x_i = x_i, so linear terms live on the diagonal.)

Variable numbering: x(node k, channel c) -> index k * (number of channels) + c
    A0 A1 A2 B0 B1 B2 C0 C1 C2 D0 D1 D2 E0 E1 E2  ->  0 1 2 ... 14
"""

import numpy as np

import config


def var_index(node_pos, channel_pos, n_channels):
    """Position of x(node, channel) in the bit vector."""
    return node_pos * n_channels + channel_pos


def build_qubo(graph, nodes=None, channels=None, penalty=None):
    """Return (Q, offset) for:  E(x) = x^T Q x + offset.

    Q is upper-triangular: Q[i,j] with i<=j holds the coefficient of x_i*x_j.

    Term 1 - interference (for every edge (u,v,w) and every channel c):
        + w * x(u,c) * x(v,c)          -> add w to Q[(u,c),(v,c)]
      Uses effective_weight (priority-scaled) if present on the edge.

    Term 2 - exactly-one-channel penalty (for every node i):
        P * (x(i,0) + x(i,1) + ... - 1)^2
      Expanding with x^2 = x:
        = P * ( 1  -  sum_c x(i,c)  +  2 * sum_{c<c'} x(i,c)*x(i,c') )
      so:  diagonal entries get  -P,  each same-node pair gets  +2P,
           and the constant  +P  goes into `offset`.
    """
    nodes = list(graph.nodes) if nodes is None else list(nodes)
    channels = config.CHANNELS if channels is None else list(channels)
    penalty = config.PENALTY if penalty is None else float(penalty)

    n_ch = len(channels)
    n_vars = len(nodes) * n_ch
    Q = np.zeros((n_vars, n_vars))
    offset = 0.0

    # Term 1: interference
    for u, v, data in graph.edges(data=True):
        weight = data.get("effective_weight", data.get("weight", 0.0))
        for c in range(n_ch):
            a = var_index(nodes.index(u), c, n_ch)
            b = var_index(nodes.index(v), c, n_ch)
            Q[min(a, b), max(a, b)] += weight

    # Term 2: exactly-one-channel penalty
    for k in range(len(nodes)):
        idxs = [var_index(k, c, n_ch) for c in range(n_ch)]
        for a in idxs:
            Q[a, a] += -penalty                 # the "- sum_c x(i,c)" part
        for p in range(n_ch):
            for q in range(p + 1, n_ch):
                Q[idxs[p], idxs[q]] += 2 * penalty   # the "2 * x x'" part
        offset += penalty                       # the constant "+1" part

    return Q, offset


def all_bitstrings(n_vars):
    """All 2^n bit vectors as a (2^n, n) 0/1 array. Row r is the binary
    number r; column k is variable x_k."""
    return (np.arange(2 ** n_vars)[:, None] >> np.arange(n_vars)) & 1


def qubo_energies(Q, offset, X):
    """E(x) = x^T Q x + offset for every row x of X."""
    return np.einsum("ni,ij,nj->n", X, Q, X) + offset


def decode(x, nodes=None, channels=None):
    """Turn a 0/1 vector into {node: channel}, or None if it breaks the
    'exactly one channel per node' rule."""
    nodes = config.NODES if nodes is None else nodes
    channels = config.CHANNELS if channels is None else channels
    n_ch = len(channels)
    assignment = {}
    for k, node in enumerate(nodes):
        chosen = [c for c in range(n_ch) if x[var_index(k, c, n_ch)] == 1]
        if len(chosen) != 1:
            return None
        assignment[node] = channels[chosen[0]]
    return assignment


def qubo_to_ising(Q, offset):
    """Convert the QUBO to an Ising Hamiltonian using x = (1 - z) / 2.

    z is a spin, +1 or -1 (x=0 -> z=+1, x=1 -> z=-1; this matches a qubit's
    Z-measurement: |0> has Z = +1, |1> has Z = -1).

    Linear term:    Q_ii * x_i        = Q_ii/2  -  (Q_ii/2) * z_i
    Pair term:      Q_ij * x_i * x_j  = Q_ij/4 * (1 - z_i - z_j + z_i*z_j)
                                      = Q_ij/4 - (Q_ij/4)*z_i - (Q_ij/4)*z_j
                                        + (Q_ij/4)*z_i*z_j

    Collecting terms:  E = const + sum_i h_i z_i + sum_{i<j} J_ij z_i z_j
        J_ij  = Q_ij / 4
        h_i   = -Q_ii / 2  -  (1/4) * (sum of every Q_ij or Q_ji touching i)
        const = offset + sum_i Q_ii / 2 + sum_{i<j} Q_ij / 4
    Returns (h, J, const) with J as {(i, j): value}.
    """
    n = Q.shape[0]
    h = np.zeros(n)
    J = {}
    const = offset
    for i in range(n):
        h[i] += -Q[i, i] / 2
        const += Q[i, i] / 2
        for j in range(i + 1, n):
            if Q[i, j] != 0:
                J[(i, j)] = Q[i, j] / 4
                h[i] += -Q[i, j] / 4
                h[j] += -Q[i, j] / 4
                const += Q[i, j] / 4
    return h, J, const


def ising_energies(h, J, const, Z):
    """Ising energy for every row z of Z (entries +1 / -1)."""
    energy = const + Z @ h
    for (i, j), value in J.items():
        energy = energy + value * Z[:, i] * Z[:, j]
    return energy
