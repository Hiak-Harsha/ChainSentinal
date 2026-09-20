"""Autonomous forensic investigation agent synthesizing taint traces, IP attribution, and Cytoscape graphs."""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from chainsentinel.evidence import canonical_hash, seal_evidence_bundle
from chainsentinel.storage.db import DatabaseManager
from chainsentinel.trace.pathfinder import InvestigativePathfinder
from chainsentinel.trace.taint_tracker import TaintTracker


class AutonomousInvestigator:
    """End-to-end autonomous forensic agent that produces tamper-evident case files."""

    def __init__(self, db: DatabaseManager):
        self.db = db
        self.tracker = TaintTracker(db)
        self.pathfinder = InvestigativePathfinder(db)

    def _canonical_hash(self, data: dict[str, Any]) -> str:
        """Compute SHA-256 digest over canonical JSON representation using evidence sealer."""
        return canonical_hash(data)

    def _get_target_metadata(self, entity_id: str) -> dict[str, Any]:
        """Fetch entity risk, classification, and transaction volume statistics."""
        conn = self.db.conn
        row = conn.execute(
            """
            SELECT e.entity_id, e.entity_type, COALESCE(a.risk_score, 0.0), e.first_seen, e.last_seen
            FROM entities e
            LEFT JOIN alerts a ON e.entity_id = a.entity_id
            WHERE e.entity_id = ?
            """,
            [entity_id],
        ).fetchone()

        if row:
            etype = str(row[1]) if row[1] else "UNKNOWN"
            rscore = float(row[2]) if row[2] is not None else 0.0
            first_ts = float(row[3]) if row[3] is not None else 0.0
            last_ts = float(row[4]) if row[4] is not None else 0.0
        else:
            etype = "UNKNOWN"
            rscore = 0.0
            first_ts = 0.0
            last_ts = 0.0

        # Address count
        addr_row = conn.execute(
            "SELECT COUNT(*) FROM address_entity_map WHERE entity_id = ?",
            [entity_id],
        ).fetchone()
        addr_count = int(addr_row[0]) if addr_row else 0

        # Inflow / Outflow volume
        vol_row = conn.execute(
            """
            WITH ent_addrs AS (SELECT address FROM address_entity_map WHERE entity_id = ?)
            SELECT 
                COALESCE((SELECT SUM(amount) FROM tx_outputs WHERE address IN (SELECT address FROM ent_addrs)), 0) as total_in,
                COALESCE((SELECT SUM(amount) FROM tx_inputs WHERE address IN (SELECT address FROM ent_addrs)), 0) as total_out
            """,
            [entity_id],
        ).fetchone()

        total_in = int(vol_row[0]) if vol_row else 0
        total_out = int(vol_row[1]) if vol_row else 0

        return {
            "entity_id": entity_id,
            "entity_type": etype,
            "risk_score": rscore,
            "address_count": addr_count,
            "total_in_sat": total_in,
            "total_out_sat": total_out,
            "first_seen_ts": first_ts,
            "last_seen_ts": last_ts,
        }

    def _get_attributed_ips_and_co_hosts(self, entity_id: str) -> dict[str, Any]:
        """Fetch attributed IPs for entity and identify co-hosted / co-originating entities."""
        conn = self.db.conn
        # 1. Attributed IPs from ip_entity_links
        ip_rows = conn.execute(
            """
            SELECT ip, score, posterior_prob, n_tx, first_seen_ratio
            FROM ip_entity_links
            WHERE entity_id = ?
            ORDER BY score DESC
            LIMIT 10
            """,
            [entity_id],
        ).fetchall()

        attributed_ips: list[dict[str, Any]] = []
        ip_list: list[str] = []
        for r in ip_rows:
            ip_str = str(r[0])
            ip_list.append(ip_str)
            attributed_ips.append({
                "ip": ip_str,
                "score": round(float(r[1]), 4) if r[1] is not None else 0.0,
                "posterior_prob": round(float(r[2]), 4) if r[2] is not None else 0.0,
                "tx_count": int(r[3]) if r[3] is not None else 0,
                "first_seen_ratio": round(float(r[4]), 4) if r[4] is not None else 0.0,
            })

        # 2. Co-hosted or shared-origin entities via these IPs
        co_entities: list[dict[str, Any]] = []
        if ip_list:
            placeholders = ",".join(["?"] * len(ip_list))
            co_rows = conn.execute(
                f"""
                SELECT l.entity_id, l.ip, l.score, COALESCE(e.entity_type, 'INDIVIDUAL'), COALESCE(a.risk_score, 0.0)
                FROM ip_entity_links l
                LEFT JOIN entities e ON l.entity_id = e.entity_id
                LEFT JOIN alerts a ON l.entity_id = a.entity_id
                WHERE l.ip IN ({placeholders}) AND l.entity_id != ?
                ORDER BY l.score DESC
                LIMIT 20
                """,
                [*ip_list, entity_id],
            ).fetchall()

            for cr in co_rows:
                co_entities.append({
                    "entity_id": str(cr[0]),
                    "shared_ip": str(cr[1]),
                    "score": round(float(cr[2]), 4) if cr[2] is not None else 0.0,
                    "entity_type": str(cr[3]),
                    "risk_score": float(cr[4]) if cr[4] is not None else 0.0,
                })

        return {
            "attributed_ips": attributed_ips,
            "shared_infrastructure_entities": co_entities,
        }

    def _build_cytoscape_subgraph(
        self,
        target_entity: str,
        target_meta: dict[str, Any],
        fwd_trace: dict[str, Any],
        bwd_trace: dict[str, Any],
        network_intel: dict[str, Any],
    ) -> dict[str, Any]:
        """Convert trace and attribution data into Cytoscape.js JSON format."""
        nodes: dict[str, dict[str, Any]] = {}
        edges: list[dict[str, Any]] = []
        edge_set: set[tuple[str, str, str]] = set()

        # 1. Target node
        nodes[target_entity] = {
            "data": {
                "id": target_entity,
                "label": f"TARGET: {target_entity}",
                "type": "TARGET",
                "entity_type": target_meta["entity_type"],
                "risk_score": target_meta["risk_score"],
                "is_target": True,
            }
        }

        # 2. Forward trace nodes and edges (Fund outflows)
        for h in fwd_trace.get("hops", []):
            u = h.get("source_entity", "")
            v = h.get("target_entity", "")
            if not u or not v:
                continue

            if u not in nodes:
                nodes[u] = {
                    "data": {
                        "id": u,
                        "label": u,
                        "type": "ENTITY",
                        "entity_type": h.get("source_type", "INDIVIDUAL"),
                        "risk_score": 0.5 if h.get("source_type") in ("DARKNET", "RANSOMWARE", "MIXER") else 0.1,
                        "is_target": False,
                    }
                }
            if v not in nodes:
                nodes[v] = {
                    "data": {
                        "id": v,
                        "label": v,
                        "type": "CASHOUT" if h.get("target_type") == "EXCHANGE" else "ENTITY",
                        "entity_type": h.get("target_type", "INDIVIDUAL"),
                        "risk_score": 0.5 if h.get("target_type") in ("DARKNET", "RANSOMWARE", "MIXER") else 0.1,
                        "is_target": False,
                    }
                }

            edge_key = (u, v, "TAINT_FLOW")
            if edge_key not in edge_set:
                edge_set.add(edge_key)
                edges.append({
                    "data": {
                        "id": f"e_{u}_{v}_{len(edges)}",
                        "source": u,
                        "target": v,
                        "label": f"{h.get('taint_pct', 0)}% taint",
                        "type": "TAINT_FLOW",
                        "weight": float(h.get("tainted_sat", 0)),
                        "taint_pct": h.get("taint_pct", 0.0),
                        "transferred_sat": h.get("transferred_sat", 0),
                        "hop_index": h.get("hop_index", 1),
                        "stop_reason": h.get("stop_reason"),
                    }
                })

        # 3. Backward trace nodes and edges (Fund inflows)
        for h in bwd_trace.get("hops", []):
            u = h.get("source_entity", "")
            v = h.get("target_entity", "")
            if not u or not v:
                continue

            if u not in nodes:
                nodes[u] = {
                    "data": {
                        "id": u,
                        "label": u,
                        "type": "FUNDING_SOURCE",
                        "entity_type": h.get("source_type", "INDIVIDUAL"),
                        "risk_score": 0.5 if h.get("source_type") in ("DARKNET", "RANSOMWARE", "MIXER") else 0.1,
                        "is_target": False,
                    }
                }
            if v not in nodes:
                nodes[v] = {
                    "data": {
                        "id": v,
                        "label": v,
                        "type": "ENTITY",
                        "entity_type": h.get("target_type", "INDIVIDUAL"),
                        "risk_score": 0.5 if h.get("target_type") in ("DARKNET", "RANSOMWARE", "MIXER") else 0.1,
                        "is_target": False,
                    }
                }

            edge_key = (u, v, "FUNDING_FLOW")
            if edge_key not in edge_set:
                edge_set.add(edge_key)
                edges.append({
                    "data": {
                        "id": f"e_{u}_{v}_{len(edges)}",
                        "source": u,
                        "target": v,
                        "label": f"Funding {h.get('taint_pct', 0)}%",
                        "type": "FUNDING_FLOW",
                        "weight": float(h.get("tainted_sat", 0)),
                        "taint_pct": h.get("taint_pct", 0.0),
                        "transferred_sat": h.get("transferred_sat", 0),
                        "hop_index": h.get("hop_index", 1),
                    }
                })

        # 4. IP nodes and attribution edges
        for ip_info in network_intel.get("attributed_ips", []):
            ip_str = ip_info["ip"]
            ip_node_id = f"IP_{ip_str}"
            if ip_node_id not in nodes:
                nodes[ip_node_id] = {
                    "data": {
                        "id": ip_node_id,
                        "label": f"IP: {ip_str}",
                        "type": "IP",
                        "score": ip_info["score"],
                        "posterior_prob": ip_info["posterior_prob"],
                        "is_target": False,
                    }
                }

            edge_key = (target_entity, ip_node_id, "ATTRIBUTED_TO")
            if edge_key not in edge_set:
                edge_set.add(edge_key)
                edges.append({
                    "data": {
                        "id": f"e_{target_entity}_{ip_node_id}",
                        "source": target_entity,
                        "target": ip_node_id,
                        "label": f"Attributed (P={ip_info['posterior_prob']})",
                        "type": "ATTRIBUTED_TO",
                        "weight": ip_info["score"],
                    }
                })

        # 5. Shared origin infrastructure edges
        for co in network_intel.get("shared_infrastructure_entities", []):
            co_id = co["entity_id"]
            shared_ip = co["shared_ip"]
            ip_node_id = f"IP_{shared_ip}"

            if co_id not in nodes:
                nodes[co_id] = {
                    "data": {
                        "id": co_id,
                        "label": f"Co-Origin: {co_id}",
                        "type": "CO_ORIGIN_ENTITY",
                        "entity_type": co.get("entity_type", "INDIVIDUAL"),
                        "risk_score": co.get("risk_score", 0.0),
                        "is_target": False,
                    }
                }

            # Connect shared entity to the IP node
            if ip_node_id in nodes:
                edge_key = (co_id, ip_node_id, "ATTRIBUTED_TO")
                if edge_key not in edge_set:
                    edge_set.add(edge_key)
                    edges.append({
                        "data": {
                            "id": f"e_{co_id}_{ip_node_id}",
                            "source": co_id,
                            "target": ip_node_id,
                            "label": f"Shared IP link (Score={co['score']})",
                            "type": "ATTRIBUTED_TO",
                            "weight": co["score"],
                        }
                    })

        return {
            "elements": {
                "nodes": list(nodes.values()),
                "edges": edges,
            }
        }

    def _generate_executive_summary(
        self,
        target_meta: dict[str, Any],
        fwd_trace: dict[str, Any],
        bwd_trace: dict[str, Any],
        network_intel: dict[str, Any],
    ) -> str:
        """Synthesize markdown narrative report of forensic findings."""
        eid = target_meta["entity_id"]
        etype = target_meta["entity_type"]
        rscore = target_meta["risk_score"]
        in_sat = target_meta["total_in_sat"]
        out_sat = target_meta["total_out_sat"]

        fwd_hops = len(fwd_trace.get("hops", []))
        bwd_hops = len(bwd_trace.get("hops", []))

        cashout_list = fwd_trace.get("summary", {}).get("cashout_exchanges", [])
        funding_list = bwd_trace.get("summary", {}).get("source_entities", [])
        ips = [i["ip"] for i in network_intel.get("attributed_ips", [])]
        co_ents = [c["entity_id"] for c in network_intel.get("shared_infrastructure_entities", [])]

        summary_lines = [
            f"# Forensic Investigation Case File: {eid}",
            f"**Classification:** `{etype}` | **Risk Score:** `{rscore:.2f}` | **Monitored Addresses:** `{target_meta['address_count']}`",
            "",
            "## 1. Executive Summary",
            f"Subject entity `{eid}` was subjected to multi-hop autonomous taint tracking and network attribution.",
            f"Total cumulative historical inflow is **{in_sat:,} satoshis** across monitored transactions, with historical outflow of **{out_sat:,} satoshis**.",
            "",
            "## 2. Liquidation & Cash-out Analysis (Forward Taint)",
            f"- Forward hops analyzed: `{fwd_hops}`",
            f"- Cash-out exchange destinations identified: {', '.join(f'`{e}`' for e in cashout_list) if cashout_list else 'None detected within hop horizon.'}",
            "",
            "## 3. Funding Origin Analysis (Backward Taint)",
            f"- Backward hops analyzed: `{bwd_hops}`",
            f"- Upstream funding sources identified: {', '.join(f'`{s}`' for s in funding_list) if funding_list else 'Direct or coinbase funding.'}",
            "",
            "## 4. Network Infrastructure & Operator Attribution",
            f"- Attributed Broadcast IPs: {', '.join(f'`{ip}`' for ip in ips) if ips else 'No high-confidence broadcast IPs attributed.'}",
            f"- Co-Origin / Shared Infrastructure Entities: {', '.join(f'`{co}`' for co in co_ents[:5]) if co_ents else 'Isolated origin fingerprint.'}",
            "",
            "## 5. Recommendation",
            "Target entity exhibits suspicious topological features consistent with layered fund dispersion." if rscore > 0.6
            else "Target entity exhibits standard commercial or individual liquidity patterns.",
        ]
        return "\n".join(summary_lines)

    def investigate(
        self,
        target: str,
        max_hops: int = 4,
        decay_model: str = "proportional",
        min_taint_ratio: float = 0.01,
        title: str | None = None,
    ) -> dict[str, Any]:
        """Execute comprehensive autonomous forensic investigation on an entity, address, or TXID."""
        resolved = self.pathfinder.resolve_entity(target)
        entity_id = resolved["entity_id"]

        # 1. Target profile
        target_meta = self._get_target_metadata(entity_id)

        # 2. Forward taint tracking
        fwd_trace = self.tracker.trace(
            root_ref=entity_id,
            direction="forward",
            max_hops=max_hops,
            decay_model=decay_model,
            min_taint_ratio=min_taint_ratio,
        )

        # 3. Backward taint tracking
        bwd_trace = self.tracker.trace(
            root_ref=entity_id,
            direction="backward",
            max_hops=max_hops,
            decay_model=decay_model,
            min_taint_ratio=min_taint_ratio,
        )

        # 4. Network attribution & shared infrastructure
        network_intel = self._get_attributed_ips_and_co_hosts(entity_id)

        # 5. Build Cytoscape graph
        subgraph = self._build_cytoscape_subgraph(
            target_entity=entity_id,
            target_meta=target_meta,
            fwd_trace=fwd_trace,
            bwd_trace=bwd_trace,
            network_intel=network_intel,
        )

        # 6. Synthesize narrative summary
        narrative = self._generate_executive_summary(
            target_meta=target_meta,
            fwd_trace=fwd_trace,
            bwd_trace=bwd_trace,
            network_intel=network_intel,
        )

        now = int(time.time())
        clean_id = entity_id.replace("ENT-", "").replace("ENT_", "").replace("ADDR_", "")[:8].upper()
        case_id = f"CASE-{clean_id}-{now}"
        case_title = title or f"Autonomous Forensic Case: {entity_id} ({target_meta['entity_type']})"

        evidence_bundle = {
            "case_id": case_id,
            "target_id": entity_id,
            "target_metadata": target_meta,
            "forward_trace_summary": fwd_trace.get("summary", {}),
            "forward_hops_count": len(fwd_trace.get("hops", [])),
            "backward_trace_summary": bwd_trace.get("summary", {}),
            "backward_hops_count": len(bwd_trace.get("hops", [])),
            "network_intelligence": network_intel,
            "cytoscape_subgraph": subgraph,
            "narrative_report": narrative,
            "created_at": now,
        }

        bundle_hash = self._canonical_hash(evidence_bundle)
        case_data = {
            "case_id": case_id,
            "target_id": entity_id,
            "title": case_title,
            "status": "OPEN",
            "bundle_hash": bundle_hash,
            "evidence_bundle": evidence_bundle,
            "narrative_report": narrative,
            "cytoscape_subgraph": subgraph,
            "created_at": now,
        }

        # Persist case file
        self.db.save_investigative_case(
            case_id=case_id,
            target_id=entity_id,
            title=case_title,
            status="OPEN",
            case_data=case_data,
        )

        return case_data
