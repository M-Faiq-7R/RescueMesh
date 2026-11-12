"""scenario.py - Schema, validation, and loader for network scenarios.

Supports JSON-based scenario files, custom nodes, channels, interference
links, weights, and node priorities. Validates topology and rejects invalid
or duplicate edges.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union


class ScenarioValidationError(ValueError):
    """Raised when a scenario fails validation."""
    pass


@dataclass
class Scenario:
    """Represents a channel allocation scenario for wireless mesh networks.

    Attributes:
        name: Human-readable scenario name.
        nodes: List of node identifiers (e.g. ['A', 'B', 'C']).
        channels: List of available channel IDs (e.g. [0, 1, 2]).
        edges: List of undirected interference edges as (node_u, node_v, weight).
        node_roles: Optional mapping of node identifier to description/role.
        node_priorities: Optional mapping of node identifier to priority multiplier (>= 1.0).
        priority_mode: Method to combine node priorities on an edge:
            'product' (p_u * p_v), 'max' (max(p_u, p_v)), 'average' ((p_u + p_v)/2), 'sum' (p_u + p_v).
        penalty: Penalty coefficient P for the exactly-one-channel constraint.
            If None, computed automatically to strictly exceed max weighted node degree.
        is_synthetic: Flag indicating whether weights are synthetic (True) or measured RF (False).
        rf_measurement: Explicit flag indicating real RF hardware measurement status.
        description: Extended description of the scenario.
        metadata: Additional contextual metadata dictionary.
    """
    name: str
    nodes: List[str]
    channels: List[Union[int, str]]
    edges: List[Tuple[str, str, float]]
    node_roles: Dict[str, str] = field(default_factory=dict)
    node_priorities: Dict[str, float] = field(default_factory=dict)
    priority_mode: str = "product"
    penalty: Optional[float] = None
    is_synthetic: bool = True
    rf_measurement: bool = False
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Validate upon creation
        self.validate()
        # Compute safe penalty if omitted
        if self.penalty is None:
            self.penalty = self.compute_safe_penalty()

    def get_effective_edge_weight(self, u: str, v: str, raw_weight: float) -> float:
        """Calculate the priority-weighted effective interference for an edge."""
        p_u = float(self.node_priorities.get(u, 1.0))
        p_v = float(self.node_priorities.get(v, 1.0))

        if self.priority_mode == "product":
            factor = p_u * p_v
        elif self.priority_mode == "max":
            factor = max(p_u, p_v)
        elif self.priority_mode == "average":
            factor = (p_u + p_v) / 2.0
        elif self.priority_mode == "sum":
            factor = p_u + p_v
        else:
            raise ScenarioValidationError(f"Unknown priority_mode: {self.priority_mode}")

        return float(raw_weight * factor)

    def compute_safe_penalty(self) -> float:
        """Compute penalty P strictly greater than the maximum weighted degree.

        This guarantees that leaving a node unassigned or assigning multiple channels
        can never be an energy-minimizing configuration.
        """
        degree_weights: Dict[str, float] = {n: 0.0 for n in self.nodes}
        for u, v, w in self.edges:
            eff_w = self.get_effective_edge_weight(u, v, w)
            degree_weights[u] += eff_w
            degree_weights[v] += eff_w

        max_deg = max(degree_weights.values()) if degree_weights else 0.0
        # Choose strictly larger integer penalty
        return float(math.ceil(max_deg) + 1.0) if max_deg > 0 else 1.0

    def validate(self) -> None:
        """Validate scenario consistency, rejecting invalid structures."""
        # 1. Validate Nodes
        if not self.nodes:
            raise ScenarioValidationError("Scenario must have at least one node.")
        if len(self.nodes) != len(set(self.nodes)):
            duplicates = [n for n in self.nodes if self.nodes.count(n) > 1]
            raise ScenarioValidationError(f"Duplicate nodes detected: {set(duplicates)}")
        for n in self.nodes:
            if not isinstance(n, str) or not n.strip():
                raise ScenarioValidationError(f"Invalid node identifier: {n!r}. Must be non-empty string.")

        # 2. Validate Channels
        if not self.channels:
            raise ScenarioValidationError("Scenario must have at least one channel.")
        if len(self.channels) != len(set(self.channels)):
            raise ScenarioValidationError(f"Duplicate channels detected: {self.channels}")

        # 3. Validate Node Priorities
        valid_nodes = set(self.nodes)
        for node, p in self.node_priorities.items():
            if node not in valid_nodes:
                raise ScenarioValidationError(f"Node priority references unknown node: {node!r}")
            if not isinstance(p, (int, float)) or math.isnan(p) or math.isinf(p) or p <= 0:
                raise ScenarioValidationError(f"Priority for node {node!r} must be positive finite number, got {p}")

        # 4. Validate Priority Mode
        if self.priority_mode not in ("product", "max", "average", "sum"):
            raise ScenarioValidationError(
                f"Invalid priority_mode '{self.priority_mode}'. Must be 'product', 'max', 'average', or 'sum'."
            )

        # 5. Validate Edges
        seen_edges = set()
        for i, edge in enumerate(self.edges):
            if not (isinstance(edge, (list, tuple)) and len(edge) == 3):
                raise ScenarioValidationError(
                    f"Edge #{i} is invalid: {edge!r}. Expected (node_u, node_v, weight)."
                )
            u, v, w = edge
            if u not in valid_nodes:
                raise ScenarioValidationError(f"Edge #{i} references unknown source node: {u!r}")
            if v not in valid_nodes:
                raise ScenarioValidationError(f"Edge #{i} references unknown target node: {v!r}")
            if u == v:
                raise ScenarioValidationError(f"Edge #{i} is a self-loop on node {u!r}. Self-loops are prohibited.")

            # Reject undirected duplicates: (u, v) is identical to (v, u)
            canonical = tuple(sorted([u, v]))
            if canonical in seen_edges:
                raise ScenarioValidationError(
                    f"Duplicate edge detected between '{canonical[0]}' and '{canonical[1]}' at edge #{i}."
                )
            seen_edges.add(canonical)

            if not isinstance(w, (int, float)) or math.isnan(w) or math.isinf(w) or w < 0:
                raise ScenarioValidationError(
                    f"Edge #{i} ({u}, {v}) has invalid weight {w!r}. Weight must be non-negative finite number."
                )

        # 6. Validate Penalty if given
        if self.penalty is not None:
            if not isinstance(self.penalty, (int, float)) or math.isnan(self.penalty) or self.penalty <= 0:
                raise ScenarioValidationError(f"Penalty must be positive number, got {self.penalty!r}")

        # 7. Real RF disclaimer check
        if self.rf_measurement:
            raise ScenarioValidationError(
                "RescueMesh simulation prohibits claiming measured RF performance without empirical laboratory data."
            )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize scenario to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "is_synthetic": self.is_synthetic,
            "rf_measurement": self.rf_measurement,
            "disclaimer": "Synthetic heuristic weights for simulation; not empirical RF/SINR measurements.",
            "nodes": list(self.nodes),
            "channels": list(self.channels),
            "edges": [[u, v, float(w)] for u, v, w in self.edges],
            "node_roles": dict(self.node_roles),
            "node_priorities": {k: float(v) for k, v in self.node_priorities.items()},
            "priority_mode": self.priority_mode,
            "penalty": float(self.penalty) if self.penalty is not None else None,
            "metadata": dict(self.metadata),
        }

    def to_json(self, filepath: Union[str, Path], indent: int = 2) -> None:
        """Write scenario to JSON file."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Scenario:
        """Create a Scenario from a dictionary, supporting multiple JSON layouts."""
        name = data.get("name", "Unnamed Scenario")
        raw_nodes = data.get("nodes", [])

        # Support list of strings or list of node objects
        nodes = []
        node_roles = dict(data.get("node_roles", {}))
        node_priorities = {k: float(v) for k, v in data.get("node_priorities", {}).items()}

        for item in raw_nodes:
            if isinstance(item, str):
                nodes.append(item)
            elif isinstance(item, dict):
                node_id = item.get("id") or item.get("name")
                if not node_id:
                    raise ScenarioValidationError(f"Node object missing 'id' or 'name': {item}")
                nodes.append(str(node_id))
                if "role" in item:
                    node_roles[str(node_id)] = str(item["role"])
                if "priority" in item:
                    node_priorities[str(node_id)] = float(item["priority"])
            else:
                raise ScenarioValidationError(f"Invalid node entry in list: {item!r}")

        channels = data.get("channels", [])

        # Support edges as [u, v, w] or {"source": u, "target": v, "weight": w}
        raw_edges = data.get("edges", [])
        edges = []
        for e in raw_edges:
            if isinstance(e, (list, tuple)) and len(e) == 3:
                edges.append((str(e[0]), str(e[1]), float(e[2])))
            elif isinstance(e, dict):
                u = e.get("source") or e.get("u") or e.get("from")
                v = e.get("target") or e.get("v") or e.get("to")
                w = e.get("weight", e.get("cost", 1.0))
                if u is None or v is None:
                    raise ScenarioValidationError(f"Edge dict missing source/target endpoints: {e}")
                edges.append((str(u), str(v), float(w)))
            else:
                raise ScenarioValidationError(f"Unrecognized edge format: {e!r}")

        return cls(
            name=name,
            nodes=nodes,
            channels=channels,
            edges=edges,
            node_roles=node_roles,
            node_priorities=node_priorities,
            priority_mode=data.get("priority_mode", "product"),
            penalty=float(data["penalty"]) if data.get("penalty") is not None else None,
            is_synthetic=data.get("is_synthetic", True),
            rf_measurement=data.get("rf_measurement", False),
            description=data.get("description", ""),
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def from_json(cls, filepath: Union[str, Path]) -> Scenario:
        """Load and validate scenario from a JSON file."""
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Scenario file not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)

    @classmethod
    def from_config(cls) -> Scenario:
        """Load default scenario directly from config.py for backwards compatibility."""
        import config
        return cls(
            name="Original RescueMesh (5-node baseline)",
            nodes=list(config.NODES),
            channels=list(config.CHANNELS),
            edges=[(u, v, float(w)) for u, v, w in config.EDGES],
            node_roles=dict(config.NODE_ROLES),
            node_priorities={n: 1.0 for n in config.NODES},
            priority_mode="product",
            penalty=float(config.PENALTY),
            is_synthetic=True,
            rf_measurement=False,
            description="Original 5-node 3-channel benchmark scenario with 3-colorable zero-interference optimum.",
            metadata={"source": "config.py"},
        )
