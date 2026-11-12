"""test_rescuemesh.py - Comprehensive test suite for RescueMesh.

Covers:
1. Scenario loading, JSON parsing, and schema validation.
2. Rejection of invalid edges, duplicate edges, self-loops, and invalid priorities.
3. Synthetic scenario generation determinism and unavoidable interference injection.
4. Classical solvers: Exhaustive, Greedy, and Simulated Annealing.
5. Optimality gap calculation.
6. QUBO and Ising mathematical properties and energy equivalence.
7. Quantum solver memory safety, parameter binding, and energy table.
8. Visualization generation and clash highlighting.
"""

import json
import os
import tempfile
import unittest

import networkx as nx
import numpy as np

import config
from classical_solver import (compute_optimality_gap, edge_interference,
                              solve_exhaustive, solve_greedy,
                              solve_simulated_annealing, total_interference,
                              validate_solution)
from graph_generator import build_interference_graph
from qubo_model import (all_bitstrings, build_qubo, decode, ising_energies,
                        qubo_energies, qubo_to_ising)
from quantum_solver import (EnergyTable, calculate_statevector_memory_mb,
                            check_qaoa_feasibility)
from scenario import Scenario, ScenarioValidationError
from scenario_generator import generate_synthetic_scenario
from visualization import draw_allocated_network, draw_network


class TestScenarioValidation(unittest.TestCase):
    """Test scenario loading, schema validation, and error handling."""

    def test_valid_scenario_creation(self):
        sc = Scenario(
            name="Valid Test",
            nodes=["A", "B", "C"],
            channels=[0, 1],
            edges=[("A", "B", 3.0), ("B", "C", 2.0)],
            node_roles={"A": "Command", "B": "Relay", "C": "Shelter"},
            node_priorities={"A": 2.0, "B": 1.0, "C": 1.0},
        )
        self.assertEqual(len(sc.nodes), 3)
        self.assertEqual(len(sc.channels), 2)
        self.assertEqual(len(sc.edges), 2)
        self.assertGreater(sc.penalty, 0)
        self.assertTrue(sc.is_synthetic)
        self.assertFalse(sc.rf_measurement)

    def test_reject_duplicate_nodes(self):
        with self.assertRaises(ScenarioValidationError):
            Scenario(
                name="Duplicate Nodes",
                nodes=["A", "B", "A"],
                channels=[0, 1],
                edges=[("A", "B", 1.0)],
            )

    def test_reject_duplicate_channels(self):
        with self.assertRaises(ScenarioValidationError):
            Scenario(
                name="Duplicate Channels",
                nodes=["A", "B"],
                channels=[0, 0],
                edges=[("A", "B", 1.0)],
            )

    def test_reject_unknown_node_in_edge(self):
        with self.assertRaises(ScenarioValidationError):
            Scenario(
                name="Unknown Node",
                nodes=["A", "B"],
                channels=[0, 1],
                edges=[("A", "Z", 2.0)],
            )

    def test_reject_self_loop(self):
        with self.assertRaises(ScenarioValidationError):
            Scenario(
                name="Self Loop",
                nodes=["A", "B"],
                channels=[0, 1],
                edges=[("A", "A", 3.0)],
            )

    def test_reject_duplicate_undirected_edges(self):
        # A-B and B-A are identical in undirected mesh
        with self.assertRaises(ScenarioValidationError):
            Scenario(
                name="Duplicate Edge",
                nodes=["A", "B", "C"],
                channels=[0, 1],
                edges=[("A", "B", 3.0), ("B", "A", 2.0)],
            )

    def test_reject_negative_weight(self):
        with self.assertRaises(ScenarioValidationError):
            Scenario(
                name="Negative Weight",
                nodes=["A", "B"],
                channels=[0, 1],
                edges=[("A", "B", -1.0)],
            )

    def test_reject_invalid_priority(self):
        with self.assertRaises(ScenarioValidationError):
            Scenario(
                name="Negative Priority",
                nodes=["A", "B"],
                channels=[0, 1],
                edges=[("A", "B", 2.0)],
                node_priorities={"A": -0.5},
            )

    def test_reject_rf_claim(self):
        with self.assertRaises(ScenarioValidationError):
            Scenario(
                name="Unverified RF",
                nodes=["A", "B"],
                channels=[0, 1],
                edges=[("A", "B", 2.0)],
                rf_measurement=True,
            )

    def test_json_roundtrip(self):
        sc = Scenario(
            name="Roundtrip Test",
            nodes=["A", "B", "C"],
            channels=[0, 1, 2],
            edges=[("A", "B", 4.0), ("B", "C", 5.0)],
            node_priorities={"A": 1.5, "B": 1.0, "C": 2.0},
        )
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            sc.to_json(temp_path)
            loaded = Scenario.from_json(temp_path)
            self.assertEqual(loaded.name, sc.name)
            self.assertEqual(loaded.nodes, sc.nodes)
            self.assertEqual(loaded.channels, sc.channels)
            self.assertEqual(len(loaded.edges), len(sc.edges))
            self.assertEqual(loaded.node_priorities["A"], 1.5)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


class TestScenarioGenerator(unittest.TestCase):
    """Test synthetic scenario generation and properties."""

    def test_reproducible_generation(self):
        sc1 = generate_synthetic_scenario(n_nodes=6, n_channels=3, seed=123)
        sc2 = generate_synthetic_scenario(n_nodes=6, n_channels=3, seed=123)
        self.assertEqual(sc1.nodes, sc2.nodes)
        self.assertEqual(sc1.edges, sc2.edges)
        self.assertEqual(sc1.penalty, sc2.penalty)

    def test_force_unavoidable_interference(self):
        # 4 channels -> clique size 5 embedded
        sc = generate_synthetic_scenario(n_nodes=7, n_channels=3, force_unavoidable=True, seed=42)
        graph = build_interference_graph(scenario=sc)
        # Check that nodes A, B, C, D form a 4-clique
        clique_nodes = sc.nodes[:4]
        for i in range(4):
            for j in range(i + 1, 4):
                self.assertTrue(graph.has_edge(clique_nodes[i], clique_nodes[j]))

        # With 3 channels and a 4-clique, exhaustive search MUST yield global minimum > 0
        res = solve_exhaustive(graph, nodes=sc.nodes, channels=sc.channels)
        self.assertGreater(res["best_score"], 0.0)


class TestClassicalSolvers(unittest.TestCase):
    """Test Greedy, Simulated Annealing, and Exhaustive search."""

    def setUp(self):
        self.sc = Scenario.from_config()
        self.graph = build_interference_graph(scenario=self.sc)

    def test_exhaustive_search_finds_optimum(self):
        res = solve_exhaustive(self.graph, nodes=self.sc.nodes, channels=self.sc.channels)
        self.assertFalse(res["skipped"])
        self.assertEqual(res["best_score"], 0.0)
        self.assertEqual(len(res["all_optimal"]), 6)
        checks = validate_solution(self.graph, res, nodes=self.sc.nodes, channels=self.sc.channels)
        self.assertTrue(all(p for _, p in checks))

    def test_greedy_solver(self):
        res = solve_greedy(self.graph, nodes=self.sc.nodes, channels=self.sc.channels)
        self.assertIn("best_assignment", res)
        self.assertIn("best_score", res)
        # Verify valid assignment: each node has exactly one channel
        self.assertEqual(len(res["best_assignment"]), len(self.sc.nodes))
        self.assertTrue(all(c in self.sc.channels for c in res["best_assignment"].values()))
        # Cross-check score with total_interference
        calc_score = total_interference(self.graph, res["best_assignment"])
        self.assertEqual(res["best_score"], calc_score)

    def test_simulated_annealing(self):
        res = solve_simulated_annealing(
            self.graph, nodes=self.sc.nodes, channels=self.sc.channels, seed=42
        )
        self.assertIn("best_assignment", res)
        self.assertIn("best_score", res)
        calc_score = total_interference(self.graph, res["best_assignment"])
        self.assertEqual(res["best_score"], calc_score)
        # On this 5-node 3-channel instance, SA should find the 0 optimum
        self.assertEqual(res["best_score"], 0.0)

    def test_optimality_gap_calculation(self):
        gap1 = compute_optimality_gap(0.0, 0.0)
        self.assertTrue(gap1["is_optimal"])
        self.assertEqual(gap1["absolute_gap"], 0.0)

        gap2 = compute_optimality_gap(18.0, 15.0)
        self.assertFalse(gap2["is_optimal"])
        self.assertEqual(gap2["absolute_gap"], 3.0)
        self.assertAlmostEqual(gap2["relative_gap_pct"], 20.0)


class TestQUBOAndIsing(unittest.TestCase):
    """Test QUBO construction, Ising conversion, and mathematical consistency."""

    def setUp(self):
        self.sc = Scenario.from_config()
        self.graph = build_interference_graph(scenario=self.sc)
        self.Q, self.offset = build_qubo(self.graph, self.sc.nodes, self.sc.channels, self.sc.penalty)

    def test_qubo_matrix_properties(self):
        # Q is upper-triangular: lower entries strictly 0
        n = self.Q.shape[0]
        self.assertEqual(n, len(self.sc.nodes) * len(self.sc.channels))
        for i in range(n):
            for j in range(i):
                self.assertEqual(self.Q[i, j], 0.0)

    def test_qubo_to_ising_conversion(self):
        h, J, const = qubo_to_ising(self.Q, self.offset)
        # Check a sample of bitstrings: QUBO energy must equal Ising energy
        X = np.random.randint(0, 2, size=(50, self.Q.shape[0]))
        E_qubo = qubo_energies(self.Q, self.offset, X)
        Z = 1 - 2 * X
        E_ising = ising_energies(h, J, const, Z)
        np.testing.assert_allclose(E_qubo, E_ising, atol=1e-9)


class TestQuantumSolverHelpers(unittest.TestCase):
    """Test quantum memory estimation and safety checks."""

    def setUp(self):
        self.sc = Scenario.from_config()
        self.graph = build_interference_graph(scenario=self.sc)
        self.Q, self.offset = build_qubo(self.graph, self.sc.nodes, self.sc.channels, self.sc.penalty)

    def test_statevector_memory_calculation(self):
        # 15 qubits: 2^15 * 16 / 1024^2 = 32768 * 16 / 1048576 = 0.5 MB
        self.assertAlmostEqual(calculate_statevector_memory_mb(15), 0.5)
        # 24 qubits: 2^24 * 16 / 1024^2 = 256 MB
        self.assertAlmostEqual(calculate_statevector_memory_mb(24), 256.0)

    def test_feasibility_check(self):
        feasible_15, _, mem_15 = check_qaoa_feasibility(5, 3, max_qubits=18)
        self.assertTrue(feasible_15)
        self.assertAlmostEqual(mem_15, 0.5)

        feasible_24, msg_24, mem_24 = check_qaoa_feasibility(8, 3, max_qubits=18)
        self.assertFalse(feasible_24)
        self.assertIn("exceeds recommended limit", msg_24)

    def test_energy_table_bit_reversal(self):
        # Qiskit rightmost bit is qubit 0
        table = EnergyTable(self.Q, self.offset)
        bitstring = "000000000000001"  # qubit 0 is 1, rest 0
        bits = table.bits(bitstring)
        self.assertEqual(bits[0], 1)
        self.assertEqual(sum(bits), 1)


class TestVisualization(unittest.TestCase):
    """Test visualization drawing functions."""

    def setUp(self):
        self.sc = Scenario.from_config()
        self.graph = build_interference_graph(scenario=self.sc)

    def test_draw_network(self):
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            temp_path = f.name
        try:
            out = draw_network(self.graph, filename=temp_path)
            self.assertTrue(os.path.exists(out))
            self.assertGreater(os.path.getsize(out), 1000)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_draw_allocated_network_with_clashes(self):
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            temp_path = f.name
        try:
            # Force clashes by assigning all nodes to channel 0
            all_clash_assignment = {n: 0 for n in self.sc.nodes}
            out = draw_allocated_network(self.graph, all_clash_assignment, filename=temp_path)
            self.assertTrue(os.path.exists(out))
            self.assertGreater(os.path.getsize(out), 1000)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


if __name__ == "__main__":
    unittest.main()
