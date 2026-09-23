"""Structural graph feature extraction and entity similarity search for ChainSentinel.

Enables investigative analysts to pivot from a suspect entity to structurally
similar entities (e.g. finding counterparties exhibiting matching mixer, darknet,
or peel-chain topology) using L2-normalized cosine distance over heterogeneous graph motifs.
"""

from __future__ import annotations

import logging
import math
from typing import Any

import numpy as np

from chainsentinel.storage.db import DatabaseManager

logger = logging.getLogger("chainsentinel.graph.embeddings")


class EntitySimilarityEngine:
    """Computes structural topology vectors and performs fast cosine similarity searches."""

    def __init__(self, db: DatabaseManager):
        self.db = db
        self._cached_entities: list[str] = []
        self._feature_matrix: np.ndarray | None = None
        self._entity_indices: dict[str, int] = {}
        self._entity_metadata: dict[str, dict[str, Any]] = {}
        self._similarity_cache: dict[tuple[str, int], list[dict[str, Any]]] = {}

    def clear_cache(self) -> None:
        """Clear indexed feature matrix and similarity search cache."""
        self._cached_entities.clear()
        self._feature_matrix = None
        self._entity_indices.clear()
        self._entity_metadata.clear()
        self._similarity_cache.clear()
        logger.info("Cleared EntitySimilarityEngine cache")


    def build_index(self) -> int:
        """Extract multi-dimensional topological vectors for all resolved entities in DuckDB."""
        conn = self.db.conn
        cursor = conn.execute(
            """
            SELECT 
                e.entity_id,
                e.entity_type,
                e.member_count,
                e.total_received_sat,
                e.total_sent_sat,
                COALESCE(s.non_standard_port_ratio, 0.0) AS non_standard_ports,
                COALESCE(s.ip_churn_rate, 0.0) AS ip_churn,
                COALESCE(s.asn_count, 1) AS asn_count,
                COALESCE(s.anonymizer_ratio, 0.0) AS anon_ratio,
                COALESCE(s.circadian_entropy, 0.5) AS circadian_entropy,
                COALESCE(COUNT(DISTINCT ge_out.target), 0) AS out_degree,
                COALESCE(COUNT(DISTINCT ge_in.source), 0) AS in_degree
            FROM entities e
            LEFT JOIN entity_network_signatures s ON e.entity_id = s.entity_id
            LEFT JOIN graph_edges ge_out ON e.entity_id = ge_out.source
            LEFT JOIN graph_edges ge_in ON e.entity_id = ge_in.target
            GROUP BY 
                e.entity_id, e.entity_type, e.member_count, e.total_received_sat,
                e.total_sent_sat, s.non_standard_port_ratio, s.ip_churn_rate,
                s.asn_count, s.anonymizer_ratio, s.circadian_entropy
            """
        )
        rows = cursor.fetchall()
        if not rows:
            logger.warning("No entities found for similarity indexing")
            return 0

        entity_ids = []
        vectors = []
        metadata = {}

        for idx, r in enumerate(rows):
            ent_id = str(r[0])
            ent_type = str(r[1])
            members = float(r[2] or 1)
            rec_sat = float(r[3] or 0)
            sent_sat = float(r[4] or 0)
            non_std_ports = float(r[5] or 0.0)
            ip_churn = float(r[6] or 0.0)
            asn_cnt = float(r[7] or 1.0)
            anon_ratio = float(r[8] or 0.0)
            circ_entropy = float(r[9] or 0.0)
            out_deg = float(r[10] or 0.0)
            in_deg = float(r[11] or 0.0)

            # Log-transform high-skew features
            log_members = math.log1p(members)
            log_rec = math.log1p(rec_sat)
            log_sent = math.log1p(sent_sat)
            log_out_deg = math.log1p(out_deg)
            log_in_deg = math.log1p(in_deg)

            vec = [
                log_members,
                log_rec,
                log_sent,
                non_std_ports,
                ip_churn,
                math.log1p(asn_cnt),
                anon_ratio,
                circ_entropy,
                log_out_deg,
                log_in_deg,
            ]
            entity_ids.append(ent_id)
            vectors.append(vec)
            metadata[ent_id] = {
                "entity_id": ent_id,
                "entity_type": ent_type,
                "member_count": int(members),
                "total_received_sat": int(rec_sat),
                "total_sent_sat": int(sent_sat),
                "anonymizer_ratio": round(anon_ratio, 3),
            }

        mat = np.array(vectors, dtype=np.float32)

        # Standardize & L2 normalize for cosine similarity
        norms = np.linalg.norm(mat, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        normalized_mat = mat / norms

        self._cached_entities = entity_ids
        self._feature_matrix = normalized_mat
        self._entity_indices = {ent_id: i for i, ent_id in enumerate(entity_ids)}
        self._entity_metadata = metadata

        logger.info("Indexed %d entities for topological similarity search", len(entity_ids))
        return len(entity_ids)

    def find_similar(self, entity_id: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Find the top-K most structurally similar entities to the target entity."""
        cache_key = (entity_id, top_k)
        if cache_key in self._similarity_cache:
            return self._similarity_cache[cache_key]

        if self._feature_matrix is None or len(self._cached_entities) == 0:
            self.build_index()

        if self._feature_matrix is None or entity_id not in self._entity_indices:
            return []

        target_idx = self._entity_indices[entity_id]
        target_vec = self._feature_matrix[target_idx]

        # Fast vector dot product = cosine similarity
        similarities = np.dot(self._feature_matrix, target_vec)

        # Sort descending
        top_indices = np.argsort(-similarities)

        results = []
        for idx in top_indices:
            cand_id = self._cached_entities[idx]
            if cand_id == entity_id:
                continue  # Skip self
            sim_score = float(similarities[idx])
            meta = self._entity_metadata.get(cand_id, {})
            results.append({
                "entity_id": cand_id,
                "similarity_score": round(max(0.0, min(1.0, sim_score)), 4),
                "entity_type": meta.get("entity_type", "UNKNOWN"),
                "member_count": meta.get("member_count", 0),
                "total_received_sat": meta.get("total_received_sat", 0),
                "total_sent_sat": meta.get("total_sent_sat", 0),
                "anonymizer_ratio": meta.get("anonymizer_ratio", 0.0),
            })
            if len(results) >= top_k:
                break

        # Evict oldest entry if cache exceeds 128 items
        if len(self._similarity_cache) >= 128:
            oldest_key = next(iter(self._similarity_cache))
            del self._similarity_cache[oldest_key]
        self._similarity_cache[cache_key] = results

        return results

