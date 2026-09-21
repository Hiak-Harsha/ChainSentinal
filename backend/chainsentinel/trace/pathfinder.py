"""Forensic pathfinding engine for computing shortest and highest-volume paths across entity graphs."""

from __future__ import annotations

import heapq
import logging
import time
from typing import Any

import networkx as nx

from chainsentinel.storage.db import DatabaseManager

logger = logging.getLogger("chainsentinel.trace.pathfinder")


class InvestigativePathfinder:
    """Computes forensic routes, bottleneck capacities, and dwell times between entities."""

    def __init__(self, db: DatabaseManager):
        self.db = db
        self._graph: nx.DiGraph | None = None
        self._last_build: float = 0.0

    def resolve_entity(self, identifier: str) -> dict[str, Any]:
        """Resolve an address, entity ID, or TXID into an entity identifier with metadata."""
        conn = self.db.conn
        identifier = identifier.strip()

        # Check if already an entity ID
        if identifier.startswith("ENT") or identifier.startswith("ADDR_") or identifier.startswith("CLUST_"):
            row = conn.execute(
                """
                SELECT e.entity_id, e.entity_type, COALESCE(a.risk_score, 0.0)
                FROM entities e
                LEFT JOIN alerts a ON e.entity_id = a.entity_id
                WHERE e.entity_id = ?
                """,
                [identifier],
            ).fetchone()
            if row:
                return {
                    "entity_id": str(row[0]),
                    "entity_type": str(row[1]) if row[1] else "UNKNOWN",
                    "risk_score": float(row[2]) if row[2] is not None else 0.0,
                }
            return {"entity_id": identifier, "entity_type": "UNKNOWN", "risk_score": 0.0}

        # Check address mapping
        row = conn.execute(
            """
            SELECT m.entity_id, COALESCE(e.entity_type, 'INDIVIDUAL'), COALESCE(a.risk_score, 0.0)
            FROM address_entity_map m
            LEFT JOIN entities e ON m.entity_id = e.entity_id
            LEFT JOIN alerts a ON m.entity_id = a.entity_id
            WHERE m.address = ?
            """,
            [identifier],
        ).fetchone()
        if row:
            return {
                "entity_id": str(row[0]),
                "entity_type": str(row[1]),
                "risk_score": float(row[2]) if row[2] is not None else 0.0,
            }

        # Check if it's a TXID
        if len(identifier) == 64:
            inp_row = conn.execute(
                """
                SELECT m.entity_id, COALESCE(e.entity_type, 'INDIVIDUAL'), COALESCE(a.risk_score, 0.0)
                FROM tx_inputs i
                JOIN address_entity_map m ON i.address = m.address
                LEFT JOIN entities e ON m.entity_id = e.entity_id
                LEFT JOIN alerts a ON m.entity_id = a.entity_id
                WHERE i.txid = ?
                LIMIT 1
                """,
                [identifier],
            ).fetchone()
            if inp_row:
                return {
                    "entity_id": str(inp_row[0]),
                    "entity_type": str(inp_row[1]),
                    "risk_score": float(inp_row[2]) if inp_row[2] is not None else 0.0,
                }

        # Default fallback
        synth_id = f"ADDR_{identifier[:8]}"
        return {"entity_id": synth_id, "entity_type": "INDIVIDUAL", "risk_score": 0.0}

    def build_graph(self, force: bool = False) -> nx.DiGraph:
        """Build directed entity-to-entity transfer graph from DuckDB."""
        # Refresh if not built or forced
        if self._graph is not None and not force:
            return self._graph

        g = nx.DiGraph()
        conn = self.db.conn

        # Load entity metadata
        entities_cursor = conn.execute(
            """
            SELECT e.entity_id, e.entity_type, COALESCE(a.risk_score, 0.0)
            FROM entities e
            LEFT JOIN alerts a ON e.entity_id = a.entity_id
            """
        )
        for eid, etype, rscore in entities_cursor.fetchall():
            g.add_node(
                eid,
                entity_id=eid,
                entity_type=etype or "INDIVIDUAL",
                risk_score=float(rscore) if rscore is not None else 0.0,
            )

        # Load entity-to-entity fund flows aggregated from transactions
        flow_query = """
        WITH in_e AS (
            SELECT 
                i.txid, 
                COALESCE(m.entity_id, 'ADDR_' || substr(i.address, 1, 8)) as src_entity,
                MIN(t.first_seen_ts) as tx_time
            FROM tx_inputs i
            JOIN transactions t ON i.txid = t.txid
            LEFT JOIN address_entity_map m ON i.address = m.address
            GROUP BY i.txid, src_entity
        ),
        out_e AS (
            SELECT 
                o.txid, 
                COALESCE(m.entity_id, 'ADDR_' || substr(o.address, 1, 8)) as dst_entity,
                SUM(o.amount) as amount_sat
            FROM tx_outputs o
            LEFT JOIN address_entity_map m ON o.address = m.address
            GROUP BY o.txid, dst_entity
        )
        SELECT 
            in_e.src_entity,
            out_e.dst_entity,
            COUNT(DISTINCT in_e.txid) as tx_count,
            SUM(out_e.amount_sat) as total_sat,
            MIN(in_e.tx_time) as first_ts,
            MAX(in_e.tx_time) as last_ts,
            LIST(in_e.txid) as txids
        FROM in_e
        JOIN out_e ON in_e.txid = out_e.txid
        WHERE in_e.src_entity != out_e.dst_entity
        GROUP BY in_e.src_entity, out_e.dst_entity
        """
        flows_cursor = conn.execute(flow_query)
        for src, dst, tx_count, total_sat, first_ts, last_ts, txids in flows_cursor.fetchall():
            if not g.has_node(src):
                g.add_node(src, entity_id=src, entity_type="INDIVIDUAL", risk_score=0.0)
            if not g.has_node(dst):
                g.add_node(dst, entity_id=dst, entity_type="INDIVIDUAL", risk_score=0.0)

            # Ensure unique txids
            unique_txids = list(dict.fromkeys(txids))[:20] if txids else []
            dwell = max(0.0, float(last_ts - first_ts)) if last_ts and first_ts else 0.0

            g.add_edge(
                src,
                dst,
                capacity=int(total_sat) if total_sat else 0,
                weight=1.0,  # unit hop distance
                tx_count=int(tx_count),
                first_ts=float(first_ts) if first_ts else 0.0,
                last_ts=float(last_ts) if last_ts else 0.0,
                dwell_sec=dwell,
                txids=unique_txids,
            )

        self._graph = g
        self._last_build = time.time()
        return self._graph

    def _fetch_origin_ips_for_txs(self, txids: list[str]) -> list[str]:
        """Fetch estimated origin IPs for a set of transactions."""
        if not txids:
            return []
        conn = self.db.conn
        try:
            placeholders = ",".join(["?"] * len(txids))
            rows = conn.execute(
                f"""
                SELECT DISTINCT COALESCE(o.origin_ip, obs.src_ip) as ip
                FROM transactions t
                LEFT JOIN tx_origins o ON t.txid = o.txid
                LEFT JOIN observations obs ON t.txid = obs.txid
                WHERE t.txid IN ({placeholders}) AND COALESCE(o.origin_ip, obs.src_ip) IS NOT NULL
                LIMIT 5
                """,
                txids,
            ).fetchall()
            return [str(r[0]) for r in rows if r[0]]
        except Exception as err:
            logger.warning("Failed to resolve origin IPs for txids: %s", err)
            return []

    def _build_path_result(
        self,
        g: nx.DiGraph,
        path: list[str],
        strategy: str,
    ) -> dict[str, Any]:
        """Assemble structured response with per-hop metrics and node telemetry."""
        hops: list[dict[str, Any]] = []
        bottleneck_sat = float("inf")
        total_volume_sat = 0
        total_dwell_sec = 0.0
        all_txids: list[str] = []

        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            edge_data = g.get_edge_data(u, v, default={})
            cap = edge_data.get("capacity", 0)
            txids = edge_data.get("txids", [])
            dwell = edge_data.get("dwell_sec", 0.0)

            bottleneck_sat = min(bottleneck_sat, cap)
            total_volume_sat += cap
            total_dwell_sec += dwell
            all_txids.extend(txids)

            origin_ips = self._fetch_origin_ips_for_txs(txids[:5])

            u_node = g.nodes.get(u, {})
            v_node = g.nodes.get(v, {})

            hops.append({
                "hop_index": i + 1,
                "source_entity": u,
                "source_type": u_node.get("entity_type", "UNKNOWN"),
                "target_entity": v,
                "target_type": v_node.get("entity_type", "UNKNOWN"),
                "volume_sat": cap,
                "tx_count": edge_data.get("tx_count", len(txids)),
                "dwell_time_sec": dwell,
                "origin_ips": origin_ips,
                "txids": txids[:10],
            })

        if bottleneck_sat == float("inf"):
            bottleneck_sat = 0

        # Node telemetry
        nodes_meta = []
        for node_id in path:
            nd = g.nodes.get(node_id, {})
            nodes_meta.append({
                "entity_id": node_id,
                "entity_type": nd.get("entity_type", "UNKNOWN"),
                "risk_score": nd.get("risk_score", 0.0),
            })

        return {
            "found": True,
            "strategy": strategy,
            "path": path,
            "hop_count": len(path) - 1,
            "bottleneck_sat": int(bottleneck_sat),
            "total_volume_sat": int(total_volume_sat),
            "total_dwell_time_sec": round(total_dwell_sec, 2),
            "hops": hops,
            "nodes": nodes_meta,
        }

    def find_shortest_path(self, source: str, target: str) -> dict[str, Any]:
        """Find path with minimum number of entity hops from source to target."""
        g = self.build_graph()
        src_info = self.resolve_entity(source)
        dst_info = self.resolve_entity(target)

        src_id = src_info["entity_id"]
        dst_id = dst_info["entity_id"]

        if src_id == dst_id:
            return {
                "found": True,
                "strategy": "shortest_path",
                "path": [src_id],
                "hop_count": 0,
                "bottleneck_sat": 0,
                "total_volume_sat": 0,
                "total_dwell_time_sec": 0.0,
                "hops": [],
                "nodes": [src_info],
            }

        if not g.has_node(src_id) or not g.has_node(dst_id):
            return {
                "found": False,
                "strategy": "shortest_path",
                "reason": f"One or both entities not found in graph: {src_id}, {dst_id}",
                "path": [],
                "hop_count": 0,
                "hops": [],
                "nodes": [],
            }

        try:
            path = nx.shortest_path(g, source=src_id, target=dst_id, weight=None)
            return self._build_path_result(g, path, strategy="shortest_path")
        except nx.NetworkXNoPath:
            return {
                "found": False,
                "strategy": "shortest_path",
                "reason": f"No directed path exists from {src_id} to {dst_id}",
                "path": [],
                "hop_count": 0,
                "hops": [],
                "nodes": [],
            }

    def find_highest_volume_path(self, source: str, target: str) -> dict[str, Any]:
        """Find the directed path that maximizes the minimum capacity (bottleneck capacity)."""
        g = self.build_graph()
        src_info = self.resolve_entity(source)
        dst_info = self.resolve_entity(target)

        src_id = src_info["entity_id"]
        dst_id = dst_info["entity_id"]

        if src_id == dst_id:
            return {
                "found": True,
                "strategy": "highest_volume_bottleneck",
                "path": [src_id],
                "hop_count": 0,
                "bottleneck_sat": 0,
                "total_volume_sat": 0,
                "total_dwell_time_sec": 0.0,
                "hops": [],
                "nodes": [src_info],
            }

        if not g.has_node(src_id) or not g.has_node(dst_id):
            return {
                "found": False,
                "strategy": "highest_volume_bottleneck",
                "reason": f"One or both entities not found in graph: {src_id}, {dst_id}",
                "path": [],
                "hop_count": 0,
                "hops": [],
                "nodes": [],
            }

        # Modified Dijkstra for Maximum Bottleneck Path (Widest Path problem)
        # Using max-heap via negated capacity in Python's heapq
        max_cap: dict[str, float] = {node: -1.0 for node in g.nodes}
        max_cap[src_id] = float("inf")
        parent: dict[str, str | None] = {src_id: None}

        # heap items: (-capacity_to_node, node)
        pq: list[tuple[float, str]] = [(-float("inf"), src_id)]

        while pq:
            neg_cap, u = heapq.heappop(pq)
            current_cap = -neg_cap

            if u == dst_id:
                break

            if current_cap < max_cap[u]:
                continue

            for v in g.successors(u):
                edge_cap = float(g[u][v].get("capacity", 0))
                path_cap = min(current_cap, edge_cap)

                if path_cap > max_cap[v]:
                    max_cap[v] = path_cap
                    parent[v] = u
                    heapq.heappush(pq, (-path_cap, v))

        if dst_id not in parent or (parent[dst_id] is None and src_id != dst_id):
            return {
                "found": False,
                "strategy": "highest_volume_bottleneck",
                "reason": f"No directed path exists from {src_id} to {dst_id}",
                "path": [],
                "hop_count": 0,
                "hops": [],
                "nodes": [],
            }

        # Reconstruct path backwards
        curr: str | None = dst_id
        path_nodes: list[str] = []
        while curr is not None:
            path_nodes.append(curr)
            curr = parent.get(curr)
        path_nodes.reverse()

        return self._build_path_result(g, path_nodes, strategy="highest_volume_bottleneck")

    def find_all_candidate_paths(
        self,
        source: str,
        target: str,
        cutoff: int = 5,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Find alternative simple paths up to cutoff hops, ranked by bottleneck capacity."""
        g = self.build_graph()
        src_info = self.resolve_entity(source)
        dst_info = self.resolve_entity(target)

        src_id = src_info["entity_id"]
        dst_id = dst_info["entity_id"]

        if not g.has_node(src_id) or not g.has_node(dst_id):
            return []

        try:
            simple_paths = list(nx.all_simple_paths(g, source=src_id, target=dst_id, cutoff=cutoff))
        except Exception as err:
            logger.warning("Error finding simple paths between %s and %s: %s", src_id, dst_id, err)
            return []

        results = []
        for p in simple_paths:
            res = self._build_path_result(g, p, strategy="candidate_path")
            results.append(res)

        # Sort descending by bottleneck sat, then ascending by hop count
        results.sort(key=lambda r: (r.get("bottleneck_sat", 0), -r.get("hop_count", 0)), reverse=True)
        return results[:limit]
