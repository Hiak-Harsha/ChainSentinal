"""Heterogeneous graph representation for forensic blockchain-network link analysis."""

from __future__ import annotations

from collections import defaultdict, deque
import json
from typing import Any


class HeteroGraph:
    """Heterogeneous forensic graph containing Address, Transaction, Entity, and IP nodes."""

    def __init__(self) -> None:
        self.nodes: dict[str, dict[str, Any]] = {}
        self.edges: list[dict[str, Any]] = []
        self._adj: dict[str, set[str]] = defaultdict(set)

    def add_node(self, node_id: str, node_type: str, label: str, **attributes: Any) -> None:
        """Register a graph node."""
        self.nodes[node_id] = {
            "id": node_id,
            "type": node_type,
            "label": label,
            **attributes,
        }

    def add_edge(
        self,
        source: str,
        target: str,
        edge_type: str,
        weight: float = 1.0,
        **metadata: Any,
    ) -> None:
        """Register a directed or bidirectional edge."""
        edge = {
            "source": source,
            "target": target,
            "edge_type": edge_type,
            "weight": weight,
            "metadata": metadata,
        }
        self.edges.append(edge)
        self._adj[source].add(target)
        self._adj[target].add(source)

    def get_ego_subgraph(
        self,
        center_id: str,
        hops: int = 2,
        max_nodes: int = 100,
    ) -> dict[str, Any]:
        """Extract a k-hop neighborhood around center_id formatted for Cytoscape.js / D3.js."""
        if center_id not in self.nodes and center_id not in self._adj:
            return {"center": center_id, "nodes": [], "edges": []}

        visited: set[str] = {center_id}
        queue: deque[tuple[str, int]] = deque([(center_id, 0)])

        while queue and len(visited) < max_nodes:
            curr, depth = queue.popleft()
            if depth >= hops:
                continue
            for neighbor in self._adj.get(curr, set()):
                if neighbor not in visited and len(visited) < max_nodes:
                    visited.add(neighbor)
                    queue.append((neighbor, depth + 1))

        # Collect relevant nodes and edges
        sub_nodes = [
            self.nodes[nid] for nid in visited if nid in self.nodes
        ]
        # Include stub nodes if not explicitly in self.nodes
        for nid in visited:
            if nid not in self.nodes:
                sub_nodes.append({"id": nid, "label": nid, "type": "UNKNOWN"})

        sub_edges = [
            e for e in self.edges
            if e["source"] in visited and e["target"] in visited
        ]

        return {
            "center": center_id,
            "nodes": sub_nodes,
            "edges": sub_edges,
            "total_nodes": len(sub_nodes),
            "total_edges": len(sub_edges),
        }

    def to_networkx(self) -> Any:
        """Convert to a NetworkX Graph if networkx is available."""
        try:
            import networkx as nx
            G = nx.MultiDiGraph()
            for nid, attrs in self.nodes.items():
                G.add_node(nid, **attrs)
            for edge in self.edges:
                G.add_edge(
                    edge["source"],
                    edge["target"],
                    edge_type=edge["edge_type"],
                    weight=edge["weight"],
                    **edge.get("metadata", {}),
                )
            return G
        except ImportError:
            return None

    def export_edge_records(self) -> list[dict[str, Any]]:
        """Export flat records suitable for DuckDB graph_edges table."""
        records = []
        for e in self.edges:
            records.append({
                "source": e["source"],
                "target": e["target"],
                "edge_type": e["edge_type"],
                "weight": e["weight"],
                "metadata_json": json.dumps(e.get("metadata", {})),
            })
        return records
