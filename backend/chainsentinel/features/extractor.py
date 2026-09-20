"""Multimodal forensic feature extraction across financial, graph, temporal, and network domains."""

from __future__ import annotations

import math
from typing import Any
import numpy as np

from chainsentinel.storage.db import DatabaseManager

FEATURE_NAMES = [
    # Financial Dynamics (10)
    "total_received_sat",
    "total_sent_sat",
    "net_flow_sat",
    "total_volume_sat",
    "avg_tx_amount_sat",
    "amount_std_sat",
    "round_amount_ratio",
    "dust_output_ratio",
    "structuring_proximity",
    "fee_to_amount_ratio",
    # Graph Topology (10)
    "member_count",
    "in_degree",
    "out_degree",
    "fan_in_ratio",
    "fan_out_ratio",
    "ego_density",
    "peel_chain_depth",
    "clustering_coefficient",
    "shared_origin_peer_count",
    "co_occurrence_max",
    # Temporal Dynamics (7)
    "lifespan_seconds",
    "tx_count",
    "tx_frequency_per_hour",
    "min_dwell_time",
    "avg_dwell_time",
    "burstiness",
    "circadian_entropy",
    # Network & Infrastructure (8)
    "origin_confidence_mean",
    "ip_churn_rate",
    "asn_count",
    "anonymizer_ratio",
    "non_standard_port_ratio",
    "geo_hop_count",
    "top_ip_posterior",
    "min_shares_origin_p_value",
]


class MultimodalFeatureExtractor:
    """Extracts 35-dimensional multimodal feature vectors for resolved entities using vectorized queries."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    def extract_all_entities(self, target_entity_id: str | None = None) -> list[dict[str, Any]]:
        """Extract complete 35-dimensional feature vectors for all entities (or a single entity) in batch."""
        conn = self.db.conn

        # 1. Base entity table
        ent_filter = f"WHERE entity_id = '{target_entity_id}'" if target_entity_id else ""
        ent_rows = conn.execute(
            f"""
            SELECT entity_id, member_count, first_seen, last_seen, total_received_sat, total_sent_sat
            FROM entities {ent_filter}
            """
        ).fetchall()

        if not ent_rows:
            return []

        entity_ids = [r[0] for r in ent_rows]
        features_map: dict[str, dict[str, float]] = {}

        for r in ent_rows:
            eid, member_count, first_seen, last_seen, rec_sat, sent_sat = r
            member_count = float(member_count or 1)
            rec_sat = float(rec_sat or 0)
            sent_sat = float(sent_sat or 0)
            fs = float(first_seen or 0)
            ls = float(last_seen or fs)
            lifespan = max(0.0, ls - fs)
            net_flow = rec_sat - sent_sat
            tot_vol = rec_sat + sent_sat

            features_map[eid] = {
                "total_received_sat": rec_sat,
                "total_sent_sat": sent_sat,
                "net_flow_sat": net_flow,
                "total_volume_sat": tot_vol,
                "member_count": member_count,
                "lifespan_seconds": lifespan,
                # Defaults to be populated by subsequent vectorized queries
                "avg_tx_amount_sat": 0.0,
                "amount_std_sat": 0.0,
                "round_amount_ratio": 0.0,
                "dust_output_ratio": 0.0,
                "structuring_proximity": 0.0,
                "fee_to_amount_ratio": 0.0,
                "in_degree": 0.0,
                "out_degree": 0.0,
                "fan_in_ratio": 1.0,
                "fan_out_ratio": 1.0,
                "ego_density": 0.0,
                "peel_chain_depth": 0.0,
                "clustering_coefficient": 0.0,
                "shared_origin_peer_count": 0.0,
                "co_occurrence_max": 0.0,
                "tx_count": 0.0,
                "tx_frequency_per_hour": 0.0,
                "min_dwell_time": 0.0,
                "avg_dwell_time": 0.0,
                "burstiness": 0.0,
                "circadian_entropy": 0.0,
                "origin_confidence_mean": 0.0,
                "ip_churn_rate": 0.0,
                "asn_count": 1.0,
                "anonymizer_ratio": 0.0,
                "non_standard_port_ratio": 0.0,
                "geo_hop_count": 0.0,
                "top_ip_posterior": 0.0,
                "min_shares_origin_p_value": 1.0,
            }

        # 2. Vectorized Financial Amounts
        aem_filter = f"WHERE a.entity_id = '{target_entity_id}'" if target_entity_id else ""
        fin_rows = conn.execute(
            f"""
            WITH ent_io AS (
                SELECT a.entity_id, i.txid, i.amount
                FROM address_entity_map a
                JOIN tx_inputs i ON a.address = i.address
                {aem_filter}
                UNION ALL
                SELECT a.entity_id, o.txid, o.amount
                FROM address_entity_map a
                JOIN tx_outputs o ON a.address = o.address
                {aem_filter}
            )
            SELECT 
                entity_id,
                COUNT(DISTINCT txid) as tx_count,
                COALESCE(AVG(amount), 0.0) as avg_amt,
                COALESCE(STDDEV(amount), 0.0) as std_amt,
                COUNT(*) FILTER (WHERE amount > 0 AND amount % 100000 = 0) * 1.0 / GREATEST(COUNT(*), 1) as round_ratio,
                COUNT(*) FILTER (WHERE amount > 0 AND amount <= 1000) * 1.0 / GREATEST(COUNT(*), 1) as dust_ratio,
                COUNT(*) FILTER (WHERE amount >= 8000000 AND amount <= 10000000) * 1.0 / GREATEST(COUNT(*), 1) as struct_ratio
            FROM ent_io
            GROUP BY entity_id
            """
        ).fetchall()

        for r in fin_rows:
            eid, tx_c, avg_a, std_a, r_ratio, d_ratio, s_ratio = r
            if eid in features_map:
                f = features_map[eid]
                f["tx_count"] = float(tx_c or 0)
                f["avg_tx_amount_sat"] = float(avg_a or 0.0)
                f["amount_std_sat"] = float(std_a or 0.0)
                f["round_amount_ratio"] = float(r_ratio or 0.0)
                f["dust_output_ratio"] = float(d_ratio or 0.0)
                f["structuring_proximity"] = float(s_ratio or 0.0)
                f["tx_frequency_per_hour"] = f["tx_count"] / max(0.1, f["lifespan_seconds"] / 3600.0)

        # 3. Vectorized Fees
        fee_rows = conn.execute(
            f"""
            WITH ent_txids AS (
                SELECT DISTINCT a.entity_id, i.txid
                FROM address_entity_map a
                JOIN tx_inputs i ON a.address = i.address
                {aem_filter}
            )
            SELECT entity_id, COALESCE(SUM(t.fee_sat), 0) as total_fees
            FROM ent_txids e
            JOIN transactions t ON e.txid = t.txid
            GROUP BY entity_id
            """
        ).fetchall()

        for eid, total_fees in fee_rows:
            if eid in features_map:
                f = features_map[eid]
                f["fee_to_amount_ratio"] = float(total_fees) / max(1.0, f["total_volume_sat"])

        # 4. Graph Degrees and Density
        deg_rows = conn.execute(
            """
            SELECT 
                target as entity_id,
                COUNT(DISTINCT source) as in_deg
            FROM graph_edges
            WHERE edge_type = 'transfers_to'
            GROUP BY target
            """
        ).fetchall()
        for eid, in_d in deg_rows:
            if eid in features_map:
                features_map[eid]["in_degree"] = float(in_d)

        out_rows = conn.execute(
            """
            SELECT 
                source as entity_id,
                COUNT(DISTINCT target) as out_deg
            FROM graph_edges
            WHERE edge_type = 'transfers_to'
            GROUP BY source
            """
        ).fetchall()
        for eid, out_d in out_rows:
            if eid in features_map:
                features_map[eid]["out_degree"] = float(out_d)

        for f in features_map.values():
            in_d = f["in_degree"]
            out_d = f["out_degree"]
            f["fan_in_ratio"] = in_d / max(1.0, out_d)
            f["fan_out_ratio"] = out_d / max(1.0, in_d)
            total_deg = in_d + out_d
            if total_deg > 1:
                # Approximated density from degree balance
                dens = min(1.0, (2.0 * min(in_d, out_d)) / max(1.0, total_deg))
                f["ego_density"] = dens
                f["clustering_coefficient"] = dens

        # 5. Peel Chain Depth
        peel_rows = conn.execute(
            f"""
            WITH peel_cands AS (
                SELECT DISTINCT a.entity_id, t.txid
                FROM address_entity_map a
                JOIN tx_inputs i ON a.address = i.address
                JOIN transactions t ON i.txid = t.txid
                WHERE t.n_in = 1 AND t.n_out = 2
            )
            SELECT entity_id, COUNT(DISTINCT txid) as peel_depth
            FROM peel_cands
            GROUP BY entity_id
            """
        ).fetchall()
        for eid, p_depth in peel_rows:
            if eid in features_map:
                features_map[eid]["peel_chain_depth"] = float(p_depth or 0)

        # 6. Shared Origin Links
        sol_rows = conn.execute(
            """
            SELECT 
                entity_id,
                COUNT(DISTINCT peer_id) as peer_count,
                COALESCE(MAX(co_occurrences), 0) as max_co,
                COALESCE(MIN(p_value), 1.0) as min_p
            FROM (
                SELECT entity_a as entity_id, entity_b as peer_id, co_occurrences, p_value FROM shares_origin_links
                UNION ALL
                SELECT entity_b as entity_id, entity_a as peer_id, co_occurrences, p_value FROM shares_origin_links
            )
            GROUP BY entity_id
            """
        ).fetchall()
        for eid, p_count, max_co, min_p in sol_rows:
            if eid in features_map:
                features_map[eid]["shared_origin_peer_count"] = float(p_count or 0)
                features_map[eid]["co_occurrence_max"] = float(max_co or 0)
                features_map[eid]["min_shares_origin_p_value"] = float(min_p if min_p is not None else 1.0)

        # 7. Network Signatures
        sig_rows = conn.execute(
            """
            SELECT entity_id, non_standard_port_ratio, ip_churn_rate, asn_count, 
                   anonymizer_ratio, circadian_entropy, geo_hop_count
            FROM entity_network_signatures
            """
        ).fetchall()
        for eid, ns_port, ip_churn, asn_c, anon_r, circ_ent, geo_hops in sig_rows:
            if eid in features_map:
                f = features_map[eid]
                f["non_standard_port_ratio"] = float(ns_port or 0.0)
                f["ip_churn_rate"] = float(ip_churn or 0.0)
                f["asn_count"] = float(asn_c or 1)
                f["anonymizer_ratio"] = float(anon_r or 0.0)
                f["circadian_entropy"] = float(circ_ent or 0.0)
                f["geo_hop_count"] = float(geo_hops or 0)
                # Burstiness correlates with circadian entropy & frequency
                if f["circadian_entropy"] > 0 and f["tx_frequency_per_hour"] > 0:
                    f["burstiness"] = min(1.0, max(-1.0, (f["circadian_entropy"] - 2.5) / 2.5))

        # 8. Origin Confidence
        orig_rows = conn.execute(
            """
            WITH ent_origins AS (
                SELECT DISTINCT a.entity_id, o.confidence
                FROM address_entity_map a
                JOIN tx_inputs i ON a.address = i.address
                JOIN tx_origins o ON i.txid = o.txid
            )
            SELECT entity_id, COALESCE(AVG(confidence), 0.0) as avg_orig_conf
            FROM ent_origins
            GROUP BY entity_id
            """
        ).fetchall()
        for eid, orig_conf in orig_rows:
            if eid in features_map:
                features_map[eid]["origin_confidence_mean"] = float(orig_conf or 0.0)

        # 9. Top IP Posterior
        post_rows = conn.execute(
            """
            SELECT entity_id, COALESCE(MAX(posterior_prob), 0.0) as max_post
            FROM ip_entity_links
            GROUP BY entity_id
            """
        ).fetchall()
        for eid, max_post in post_rows:
            if eid in features_map:
                features_map[eid]["top_ip_posterior"] = float(max_post or 0.0)

        # 10. Dwell Times
        dwell_rows = conn.execute(
            """
            WITH recv_min AS (
                SELECT a.entity_id, MIN(t.first_seen_ts) as min_recv, AVG(t.first_seen_ts) as avg_recv
                FROM address_entity_map a
                JOIN tx_outputs o ON a.address = o.address
                JOIN transactions t ON o.txid = t.txid
                GROUP BY a.entity_id
            ),
            spend_min AS (
                SELECT a.entity_id, MIN(t.first_seen_ts) as min_spend, AVG(t.first_seen_ts) as avg_spend
                FROM address_entity_map a
                JOIN tx_inputs i ON a.address = i.address
                JOIN transactions t ON i.txid = t.txid
                GROUP BY a.entity_id
            )
            SELECT r.entity_id, 
                   GREATEST(0.0, COALESCE(s.min_spend - r.min_recv, 0.0)) as min_dwell,
                   GREATEST(0.0, COALESCE(s.avg_spend - r.avg_recv, 0.0)) as avg_dwell
            FROM recv_min r
            LEFT JOIN spend_min s ON r.entity_id = s.entity_id
            """
        ).fetchall()
        for eid, min_d, avg_d in dwell_rows:
            if eid in features_map:
                features_map[eid]["min_dwell_time"] = float(min_d or 0.0)
                features_map[eid]["avg_dwell_time"] = float(avg_d or 0.0)

        # Sanitize NaNs and return list of dicts
        results = []
        for eid in entity_ids:
            f_dict = features_map.get(eid, {fn: 0.0 for fn in FEATURE_NAMES})
            for k, v in f_dict.items():
                if math.isnan(v) or math.isinf(v):
                    f_dict[k] = 0.0
            results.append({
                "entity_id": eid,
                "features": f_dict,
            })

        return results

    def extract_entity_features(self, entity_id: str) -> dict[str, float]:
        """Extract complete 35-dimensional feature dictionary for a single entity."""
        res = self.extract_all_entities(target_entity_id=entity_id)
        if res:
            return res[0]["features"]
        return {fname: 0.0 for fname in FEATURE_NAMES}

    def extract_all_and_save(self) -> list[dict[str, Any]]:
        """Extract multimodal features for all entities and persist to DuckDB entity_features."""
        extracted_rows = self.extract_all_entities()
        if extracted_rows:
            self.db.save_entity_features_batch(extracted_rows)
        return extracted_rows
