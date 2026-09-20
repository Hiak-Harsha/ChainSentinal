"""Correlation engine orchestrating origin estimation, TF-IDF association, timing analysis, and signatures."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
import json
import time
from typing import Any

from chainsentinel.correlate.association_matrix import AssociationMatrix
from chainsentinel.correlate.behavioral_signatures import BehavioralSignatureExtractor, NetworkSignature
from chainsentinel.correlate.origin_estimator import OriginEstimate, OriginEstimator
from chainsentinel.correlate.timing_correlator import SharesOriginLink, TimingCorrelator
from chainsentinel.storage.db import DatabaseManager


@dataclass
class CorrelationSummary:
    total_tx_analyzed: int = 0
    total_entities_analyzed: int = 0
    total_origin_estimates: int = 0
    total_ip_entity_links: int = 0
    total_operator_links: int = 0
    total_signatures_extracted: int = 0
    duration_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_tx_analyzed": self.total_tx_analyzed,
            "total_entities_analyzed": self.total_entities_analyzed,
            "total_origin_estimates": self.total_origin_estimates,
            "total_ip_entity_links": self.total_ip_entity_links,
            "total_operator_links": self.total_operator_links,
            "total_signatures_extracted": self.total_signatures_extracted,
            "duration_seconds": round(self.duration_seconds, 3),
        }


class CorrelationEngine:
    """Orchestrates network-blockchain correlation pipeline."""

    def __init__(
        self,
        db: DatabaseManager,
        time_window_sec: float = 60.0,
        p_value_thresh: float = 0.05,
        num_permutations: int = 100,
    ) -> None:
        self.db = db
        self.origin_estimator = OriginEstimator()
        self.association_matrix = AssociationMatrix()
        self.timing_correlator = TimingCorrelator(
            time_window_sec=time_window_sec,
            num_permutations=num_permutations,
            p_value_threshold=p_value_thresh,
        )

    def run(self) -> tuple[CorrelationSummary, dict[str, list[dict[str, Any]]]]:
        """Execute complete correlation pipeline and persist to DuckDB."""
        start_time = time.time()
        summary = CorrelationSummary()

        # 1. Fetch observations, inputs, and address-entity mapping
        obs_cursor = self.db.conn.execute(
            "SELECT obs_id, ts, src_ip, dst_ip, src_port, dst_port, txid, src_country, src_asn, is_anonymizer, sensor_id FROM observations"
        )
        obs_cols = [desc[0] for desc in obs_cursor.description]
        all_obs = [dict(zip(obs_cols, r)) for r in obs_cursor.fetchall()]

        # Group observations by txid
        obs_by_txid: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for ob in all_obs:
            obs_by_txid[ob["txid"]].append(ob)

        # Map addresses to entity_ids
        aem_cursor = self.db.conn.execute("SELECT address, entity_id FROM address_entity_map")
        addr_to_entity = dict(aem_cursor.fetchall())

        # Map txids to sending entity_id (via inputs)
        in_cursor = self.db.conn.execute("SELECT txid, address FROM tx_inputs")
        entity_txids: dict[str, list[str]] = defaultdict(list)
        seen_entity_tx: set[tuple[str, str]] = set()

        for txid, addr in in_cursor.fetchall():
            ent_id = addr_to_entity.get(addr)
            if ent_id and (ent_id, txid) not in seen_entity_tx:
                seen_entity_tx.add((ent_id, txid))
                entity_txids[ent_id].append(txid)

        summary.total_tx_analyzed = len(obs_by_txid)
        summary.total_entities_analyzed = len(entity_txids)

        # 2. Origin Estimation
        origin_estimates = self.origin_estimator.estimate_batch(obs_by_txid)
        summary.total_origin_estimates = len(origin_estimates)

        tx_origins_batch: list[dict[str, Any]] = [
            est.to_dict() for est in origin_estimates.values()
        ]

        # 3. Hub-Relay De-biasing & TF-IDF Association Matrix
        associations = self.association_matrix.compute_associations(
            entity_txids=entity_txids,
            origin_estimates=origin_estimates,
        )

        ip_entity_links_batch: list[dict[str, Any]] = []
        for ent_id, ips in associations.items():
            for ip_info in ips:
                ip_entity_links_batch.append(ip_info)

        summary.total_ip_entity_links = len(ip_entity_links_batch)

        # 4. Timing Correlation & Permutation Tests (Operator Links)
        operator_links = self.timing_correlator.find_operator_links(
            entity_txids=entity_txids,
            origin_estimates=origin_estimates,
        )
        summary.total_operator_links = len(operator_links)

        shares_origin_batch = [link.to_dict() for link in operator_links]

        # 5. Extract Behavioral Signatures per Entity
        signatures_batch: list[dict[str, Any]] = []
        for ent_id, txids in entity_txids.items():
            ent_obs: list[dict[str, Any]] = []
            for txid in txids:
                ent_obs.extend(obs_by_txid.get(txid, []))
            sig = BehavioralSignatureExtractor.extract(
                entity_id=ent_id,
                observations=ent_obs,
                tx_count=len(txids),
            )
            signatures_batch.append(sig.to_dict())

        summary.total_signatures_extracted = len(signatures_batch)

        # 6. Graph Edges for shares_origin
        graph_edges_batch: list[dict[str, Any]] = []
        for link in operator_links:
            graph_edges_batch.append({
                "source": link.entity_a,
                "target": link.entity_b,
                "edge_type": "shares_origin",
                "weight": round(1.0 - link.p_value, 4),
                "metadata_json": json.dumps({
                    "shared_ip": link.shared_ip,
                    "co_occurrences": link.co_occurrences,
                    "p_value": link.p_value,
                }),
            })

        # 7. Persist to DuckDB
        self.db.clear_correlation_data()
        self.db.insert_tx_origins_batch(tx_origins_batch)
        self.db.insert_ip_entity_links_batch(ip_entity_links_batch)
        self.db.insert_shares_origin_links_batch(shares_origin_batch)
        self.db.insert_entity_network_signatures_batch(signatures_batch)
        if graph_edges_batch:
            self.db.insert_graph_edges_batch(graph_edges_batch)

        summary.duration_seconds = time.time() - start_time
        return summary, associations
