"""config.py - the ONE place where the problem instance is defined.

Change the numbers here and the rest of the project follows.
All interference weights are synthetic (made up for the simulation).
"""

# Communication nodes (vertices of the graph)
NODES = ["A", "B", "C", "D", "E"]

# Available wireless channels (the limited spectrum)
CHANNELS = [0, 1, 2]

# Interference edges: (node_1, node_2, weight)
# A bigger weight = more severe interference if both nodes share a channel.
EDGES = [
    ("A", "B", 5),
    ("A", "C", 2),
    ("B", "C", 4),
    ("B", "D", 3),
    ("C", "D", 6),
    ("C", "E", 2),
    ("D", "E", 5),
]

# Penalty coefficient P for the "exactly one channel per node" rule.
# Chosen as 15 because the largest weighted degree in this graph is 14
# (node C: 2+4+6+2), and a safe P should be strictly larger than that.
# Not used by the classical solver, only by the QUBO model (Phase 3).
PENALTY = 15

# What each node represents in the disaster scenario (used for the plot/report).
NODE_ROLES = {
    "A": "Command center",
    "B": "Rescue team 1",
    "C": "Medical unit",
    "D": "Rescue team 2",
    "E": "Emergency shelter",
}
